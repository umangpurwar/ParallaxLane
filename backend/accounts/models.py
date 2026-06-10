from django.contrib.auth.models import AbstractUser
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
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.otp}"