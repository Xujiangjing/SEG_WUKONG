import time
import os
from django.test import TestCase, override_settings
from django.core.mail import send_mail
from tickets.models import Ticket, Department
from tickets.management.commands.fetch_emails import Command
from django.conf import settings

@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
    EMAIL_HOST='smtp.gmail.com',
    EMAIL_PORT=587,
    EMAIL_USE_TLS=True,
    EMAIL_HOST_USER='wukonghelpdesk@gmail.com',
    EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD', ''),  
)

class RealFetchEmailsTest(TestCase):
    """Use real email settings to test the fetch_emails command"""

    def setUp(self):
        """Create a Department for the Ticket"""
        Department.objects.create(name="general_enquiry")

    def test_real_fetch_emails(self):
        """
        Real Integration Test for Fetching Emails
        1.Student sends an email to Help Desk (via real SMTP);
        2.Wait for Gmail to receive the email;
        3.Run the fetch_emails command to read unread emails from Gmail;
        4️.Create a Ticket and send a confirmation email to the student.
        """
        # Send a test email from student to Help Desk
        student_email = "wukonghelpdesk@gmail.com"  # use the same email for testing
        ticket_title = "Test Ticket for Real Email"
        send_mail(
            subject=ticket_title,
            message="This is a test email for Help Desk.",
            from_email=student_email,
            recipient_list=["wukonghelpdesk@gmail.com"],
            fail_silently=False,
        )

        # Wait for Gmail to receive the email
        time.sleep(20)  # wait for Gmail to receive the email

        # Run the fetch_emails command to read unread emails from Gmail
        command = Command()
        command.handle()

        # 4️⃣ Check if a Ticket is created
        tickets = Ticket.objects.all()
        self.assertTrue(tickets.exists(), "❌ Ticket not created")


