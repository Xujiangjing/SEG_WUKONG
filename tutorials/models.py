from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ValidationError
from libgravatar import Gravatar
import uuid

class Department(models.Model):
    """Model used to represent a department in Django Admin."""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    responsible_roles = models.CharField(
        max_length=255,
        help_text="Comma-separated roles responsible for this department, e.g., 'specialists'",
        default='program_officers' 
    )
    def __str__(self):
        return self.name
    
class User(AbstractUser):
    """Custom User model with roles and optional department association."""
    ROLE_CHOICES = [
        ('students', 'Students'),
        ('program_officers', 'Program Officers'),
        ('specialists', 'Specialists'),
        ('others', 'Others'), # Admins, superusers, etc.
    ]

    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[RegexValidator(
            regex=r'^@\w{3,}$',
            message='Username must consist of @ followed by at least three alphanumericals'
        )]
    )
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=False)
    email = models.EmailField(unique=True, blank=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='students')
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    class Meta:
        """Model options."""

        ordering = ['last_name', 'first_name']
    
    def clean(self):
        # Specialists must have a department
        if self.role == 'specialists' and not self.department:
            raise ValidationError("Specialists must have a department.")

    def full_name(self):
        """Return a string containing the user's full name."""

        return f'{self.first_name} {self.last_name}'

    def gravatar(self, size=120):
        """Return a URL to the user's gravatar."""

        gravatar_object = Gravatar(self.email)
        gravatar_url = gravatar_object.get_image(size=size, default='mp')
        return gravatar_url

    def mini_gravatar(self):
        """Return a URL to a miniature version of the user's gravatar."""
        
        return self.gravatar(size=60)

    def is_student(self):
        return self.role == 'students'
    
    def is_program_officer(self):
        return self.role == 'program_officers'
    
    def is_specialist(self):
        return self.role == 'specialists'
    
    def __str__(self):
        if self.department:
            return f"{self.username} ({self.role}) - {self.department}"
        return f"{self.username} ({self.role})"