"""Organisation application and approval lifecycle."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils.text import slugify
from django.utils.timezone import now

from admin_panel.audit import audit
from core.validators import validate_org_name
from exams.models import ExamAttempt
from exams.services import REASON_ORG_SUSPENDED, finalize_attempt

from .models import Organisation, OrganisationMember

User = get_user_model()

# (current status, action) -> new status. Anything else is an invalid transition.
TRANSITIONS = {
    (Organisation.STATUS_PENDING, "approve"): Organisation.STATUS_APPROVED,
    (Organisation.STATUS_PENDING, "reject"): Organisation.STATUS_REJECTED,
    (Organisation.STATUS_APPROVED, "suspend"): Organisation.STATUS_SUSPENDED,
    (Organisation.STATUS_SUSPENDED, "reactivate"): Organisation.STATUS_APPROVED,
}
NOTE_REQUIRED = {"reject", "suspend"}
MAX_TEXT = {"description": 2000, "contact_phone": 30, "website": 200}


class ApplicationError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def is_platform_account(user):
    """Super admins (and Django staff) never act as organisation members."""
    return bool(user and (user.is_superuser or user.is_staff))


def _clean_details(data, require_name=True):
    """Validate the public application fields. Unknown fields are ignored."""
    details = {}
    if require_name or "name" in data:
        try:
            details["name"] = validate_org_name(data.get("name"))
        except ValueError as exc:
            raise ApplicationError("invalid_name", str(exc))
    for field, limit in MAX_TEXT.items():
        if field in data:
            value = str(data.get(field) or "").strip()
            if len(value) > limit:
                raise ApplicationError("invalid_request", f"{field} must be {limit} characters or fewer")
            details[field] = value
    if require_name and not details.get("description"):
        raise ApplicationError("invalid_request", "Describe your organisation and how it will use exams")
    if details.get("website") and not details["website"].startswith(("http://", "https://")):
        raise ApplicationError("invalid_request", "website must start with http:// or https://")
    return details


def _name_taken(name, exclude_id=None):
    qs = Organisation.objects.filter(name__iexact=name).exclude(status=Organisation.STATUS_REJECTED)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()


def submit_application(user, data):
    """Create a pending organisation owned by `user`. Raises ApplicationError."""
    if is_platform_account(user):
        raise ApplicationError("registration_not_allowed", "This account cannot register an organisation", 403)
    if not user.email_verified:
        raise ApplicationError("email_not_verified", "Verify your email before applying", 403)
    details = _clean_details(data)

    with transaction.atomic():
        # Serialises concurrent applications from the same account.
        User.objects.select_for_update().get(pk=user.pk)
        owned = Organisation.objects.filter(owner=user)
        if owned.filter(status=Organisation.STATUS_PENDING).exists():
            raise ApplicationError("application_pending", "You already have an application waiting for review", 409)
        if owned.filter(status=Organisation.STATUS_REJECTED).exists() and not owned.exclude(
            status=Organisation.STATUS_REJECTED
        ).exists():
            raise ApplicationError(
                "application_rejected",
                "Your previous application was rejected. Update and resubmit it instead of applying again.",
                409,
            )
        if owned.filter(status__in=[Organisation.STATUS_APPROVED, Organisation.STATUS_SUSPENDED]).exists():
            raise ApplicationError("organisation_exists", "You already own an organisation", 409)
        if _name_taken(details["name"]):
            raise ApplicationError("name_taken", "An organisation with this name already exists", 409)

        base_slug = slugify(details["name"]) or "org"
        slug, counter = base_slug, 1
        while Organisation.objects.filter(slug=slug).exists():
            slug, counter = f"{base_slug}-{counter}", counter + 1
        try:
            with transaction.atomic():
                org = Organisation.objects.create(
                    owner=user, slug=slug, status=Organisation.STATUS_PENDING, submitted_at=now(), **details
                )
                OrganisationMember.objects.create(organisation=org, user=user, role=OrganisationMember.ROLE_OWNER)
        except IntegrityError:
            # Lost a race on the name or slug against another applicant.
            raise ApplicationError("name_taken", "An organisation with this name already exists", 409)
        audit(user, "application_submitted", org, target=org.name)
    return org


def update_application(user, org_id, data, resubmit=False):
    """Owner edits a pending application, or edits and resubmits a rejected one."""
    with transaction.atomic():
        org = Organisation.objects.select_for_update().filter(pk=org_id, owner=user).first()
        if org is None:
            raise ApplicationError("not_found", "Application not found", 404)
        allowed = Organisation.STATUS_REJECTED if resubmit else Organisation.STATUS_PENDING
        if org.status != allowed:
            raise ApplicationError(
                "invalid_state",
                "Only rejected applications can be resubmitted" if resubmit else "Only pending applications can be edited",
                409,
            )
        details = _clean_details(data, require_name=False)
        if "name" in details and _name_taken(details["name"], exclude_id=org.pk):
            raise ApplicationError("name_taken", "An organisation with this name already exists", 409)
        for field, value in details.items():
            setattr(org, field, value)
        if resubmit:
            org.status = Organisation.STATUS_PENDING
            org.submitted_at = now()
        try:
            with transaction.atomic():
                org.save()
        except IntegrityError:
            raise ApplicationError("name_taken", "An organisation with this name already exists", 409)
        audit(user, "application_resubmitted" if resubmit else "application_updated", org, target=org.name)
    return org


def review_organisation(org_id, action, actor, note=""):
    """Super admin transition. Raises ApplicationError for invalid transitions."""
    note = (note or "").strip()[:2000]
    if action in NOTE_REQUIRED and not note:
        raise ApplicationError("note_required", "A reason is required for this action")
    with transaction.atomic():
        org = Organisation.objects.select_for_update().filter(pk=org_id).first()
        if org is None:
            raise ApplicationError("not_found", "Organisation not found", 404)
        new_status = TRANSITIONS.get((org.status, action))
        if new_status is None:
            raise ApplicationError(
                "invalid_transition", f"Cannot {action} an organisation that is {org.status}", 409
            )
        previous = org.status
        org.status = new_status
        org.review_note = note
        org.reviewed_by = actor
        org.reviewed_at = now()
        org.save(update_fields=["status", "review_note", "reviewed_by", "reviewed_at"])

        ended = 0
        if new_status == Organisation.STATUS_SUSPENDED:
            # Suspension stops running exams; saved answers are still graded.
            for attempt in ExamAttempt.objects.select_for_update().select_related("exam").filter(
                exam__organisation=org, status="active"
            ):
                finalize_attempt(attempt, "terminated", REASON_ORG_SUSPENDED)
                ended += 1
        audit(actor, f"organisation_{action}", org, target=org.name,
              previous_status=previous, new_status=new_status, note=note, attempts_ended=ended)
    return org
