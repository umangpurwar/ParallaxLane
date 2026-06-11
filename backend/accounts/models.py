from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.db import models


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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

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