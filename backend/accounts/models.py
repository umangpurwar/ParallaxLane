from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):

    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("candidate", "Candidate"),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="candidate"
    )

    email = models.EmailField(unique=True)

   
    name = models.CharField(max_length=100, blank=True)

    current_organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_users'
    )

    # Separates "never verified" from "deactivated by an administrator":
    # only unverified inactive accounts may complete OTP registration.
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"), name="unique_user_email_ci"
            ),
        ]

    def save(self, *args, **kwargs):
        # One canonical form for every creation path (API, createsuperuser, admin).
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
    
    
class EmailOTP(models.Model):
    email = models.EmailField(db_index=True)
    otp_hash = models.CharField(max_length=128)  # Store hashed OTP
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "created_at"], name="emailotp_email_created_idx"),
        ]

    def set_otp(self, otp):
        self.otp_hash = make_password(otp)

    def check_otp(self, otp):
        return check_password(otp, self.otp_hash)

    # Backward compatibility: accept 'otp' parameter when creating
    def __init__(self, *args, **kwargs):
        otp_value = kwargs.pop('otp', None)
        super().__init__(*args, **kwargs)
        if otp_value:
            self.set_otp(otp_value)

    def __str__(self):
        return f"{self.email} - OTP"


class UserDevice(models.Model):
    """A candidate's exam device: hashed Android ID + Keystore public key."""

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REVOKED = "revoked"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REVOKED, "Revoked"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    # SHA-256 hex computed on the phone from ANDROID_ID; the raw ID never leaves it.
    device_id = models.CharField(max_length=64, db_index=True)
    # Base64 X.509 SubjectPublicKeyInfo of an EC P-256 Android Keystore key.
    public_key = models.TextField()
    model_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    pending_reason = models.CharField(max_length=40, blank=True)
    approved_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(status="approved"),
                name="one_approved_device_per_user",
            ),
            models.UniqueConstraint(
                fields=["user", "device_id"],
                condition=~models.Q(status="revoked"),
                name="unique_live_device_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.device_id[:8]} ({self.status})"
