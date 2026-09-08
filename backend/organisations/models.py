from django.db import models
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
    
    # Join Code Fields
    join_code = models.CharField(max_length=6, unique=True, db_index=True, null=True, blank=True)
    join_code_enabled = models.BooleanField(default=False)
    join_code_valid_from = models.DateTimeField(null=True, blank=True, default=now)
    join_code_valid_until = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
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

    expires_at = models.DateTimeField(null=True, blank=True)
    is_revoked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "accepted"], name="orginvite_email_accepted_idx"),
        ]

    def __str__(self):
        return f"{self.email} -> {self.organisation}"
