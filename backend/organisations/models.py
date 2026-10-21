from django.db import models
from django.db.models.functions import Lower
from django.conf import settings
import secrets
import string
from django.utils.timezone import now


def generate_join_code():
    """Generate a unique, human-readable join code (6 characters, uppercase alphanumeric)."""
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(6))
        if not Organisation.objects.filter(join_code=code).exists():
            return code


class Organisation(models.Model):

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_orgs'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # Approval lifecycle. is_active is derived from status in save() and is
    # what every member/admin endpoint filters on, so only approved
    # organisations can operate.
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending review"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_SUSPENDED, "Suspended"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    description = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    review_note = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_orgs",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(default=now)
    is_active = models.BooleanField(default=False)

    
    # Join Code Fields
    join_code = models.CharField(max_length=6, unique=True, db_index=True, null=True, blank=True)
    join_code_enabled = models.BooleanField(default=False)
    join_code_valid_from = models.DateTimeField(null=True, blank=True, default=now)
    join_code_valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # One live organisation name (case-insensitive); rejected names can be reused.
            models.UniqueConstraint(
                Lower("name"),
                condition=~models.Q(status="rejected"),
                name="unique_live_org_name_ci",
            ),
            # A user can have only one application waiting for review.
            models.UniqueConstraint(
                fields=["owner"],
                condition=models.Q(status="pending"),
                name="one_pending_application_per_owner",
            ),
        ]

    def save(self, *args, **kwargs):
        self.is_active = self.status == self.STATUS_APPROVED
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "status" in update_fields and "is_active" not in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["is_active"]
        if not self.join_code:
            self.join_code = generate_join_code()
        super().save(*args, **kwargs)

    def regenerate_join_code(self):
        """Generate a new unique join code for this organisation."""
        self.join_code = generate_join_code()
        self.save(update_fields=["join_code"])
    
    def is_join_code_valid(self):
        """Check if the join code is enabled and within valid time window."""
        if not self.join_code_enabled:
            return False
        
        current_time = now()
        
        if self.join_code_valid_from and current_time < self.join_code_valid_from:
            return False
        
        if self.join_code_valid_until and current_time > self.join_code_valid_until:
            return False
        
        return True

    def __str__(self):
        return self.name


class OrganisationMember(models.Model):

    ROLE_OWNER = "owner"
    ROLE_ADMIN = "admin"
    ROLE_INVIGILATOR = "invigilator"
    ROLE_CANDIDATE = "candidate"

    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_ADMIN, "Admin"),
        (ROLE_INVIGILATOR, "Invigilator"),
        (ROLE_CANDIDATE, "Candidate"),
    ]

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='members'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships'
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_exam_enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organisation', 'user')

    def __str__(self):
        return f"{self.user} @ {self.organisation} ({self.role})"


class OrganisationInvite(models.Model):
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="invites"
    )

    email = models.EmailField()
    role = models.CharField(max_length=20, default="candidate")
    token = models.CharField(max_length=100, unique=True)

    accepted = models.BooleanField(default=False)
    declined = models.BooleanField(default=False)

    expires_at = models.DateTimeField(null=True, blank=True)
    is_revoked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "accepted"], name="orginvite_email_accepted_idx"),
        ]

    def __str__(self):
        return f"{self.email} -> {self.organisation}"
