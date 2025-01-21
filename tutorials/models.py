from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractUser
from django.db import models
from libgravatar import Gravatar
import uuid

class User(AbstractUser):
    """Model used for user authentication, and team member related information."""

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


    class Meta:
        """Model options."""

        ordering = ['last_name', 'first_name']

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

class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    DEPARTMENT_CHOICES = [
        ('general_enquiry', 'General Enquiry'),
        ('academic_support', 'Academic Support'),
        ('health_services', 'Health Services'),
        ('financial_aid', 'Financial Aid'),
        ('career_services', 'Career Services'),
        ('welfare', 'Welfare'),
        ('misconduct', 'Misconduct'),
        ('it_support', 'IT Support'),
        ('housing', 'Housing and Accommodation'),
        ('admissions', 'Admissions'),
        ('library_services', 'Library Services'),
        ('research_support', 'Research Support'),
        ('study_abroad', 'Study Abroad'),
        ('alumni_relations', 'Alumni Relations'),
        ('exam_office', 'Examinations Office'),
        ('security', 'Campus Security'),
        ('language_centre', 'Language Centre'),
    ]

    ACTION_CHOICES = [
        ('created', 'Created'),
        ('status_updated', 'Status Updated'),
        ('priority_updated', 'Priority Updated'),
        ('redirected', 'Redirected'),
        ('responded', 'Responded'),
        ('closed', 'Closed'),
    ]

    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_tickets')
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='low')
    assigned_department = models.CharField(
        max_length=50,
        choices=DEPARTMENT_CHOICES,
        default='general_enquiry'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    latest_action = models.CharField(max_length=20, choices=ACTION_CHOICES, blank=True, null=True)
    latest_editor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='edited_tickets')

    def __str__(self):
        return f"Ticket {self.id}: {self.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if self.latest_action == None:  # If no action has yet been recorded, set a default action
            self.latest_action = 'created'
        super().save(*args, **kwargs)

class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment {self.id} for Ticket {self.ticket.id}"

class TicketActivity(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='activity_log')
    action = models.CharField(max_length=100, choices=Ticket.ACTION_CHOICES)
    action_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='action_taken_by')
    action_time = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Activity for Ticket {self.ticket.id} by {self.action_by.username} on {self.action_time}"