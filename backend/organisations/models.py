from django.db import models
from django.conf import settings


class Organisation(models.Model):

    PLAN_FREE = "free"
    PLAN_PRO = "pro"
    PLAN_ENTERPRISE = "enterprise"

    PLAN_CHOICES = [
        (PLAN_FREE, "Free"),
        (PLAN_PRO, "Pro"),
        (PLAN_ENTERPRISE, "Enterprise"),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)

    plan = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        default=PLAN_FREE
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_orgs'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # limits
    max_exams = models.IntegerField(default=3)
    max_candidates = models.IntegerField(default=30)
    proctoring_enabled = models.BooleanField(default=False)

    max_admins = models.IntegerField(default=2)
    max_invigilators = models.IntegerField(default=5)

    def __str__(self):
        return f"{self.name} ({self.plan})"


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

    expires_at = models.DateTimeField(null=True, blank=True)
    is_revoked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "accepted"], name="orginvite_email_accepted_idx"),
        ]

    def __str__(self):
        return f"{self.email} -> {self.organisation}"


class Coupon(models.Model):
    PLAN_CHOICES = Organisation.PLAN_CHOICES

    code = models.CharField(max_length=50, unique=True)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(default=100)
    used_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} → {self.plan}"

    @property
    def is_expired(self):
        from django.utils.timezone import now
        return self.expires_at is not None and now() > self.expires_at

    @property
    def is_exhausted(self):
        return self.used_count >= self.max_uses

    def is_redeemable(self):
        return self.active and not self.is_expired and not self.is_exhausted