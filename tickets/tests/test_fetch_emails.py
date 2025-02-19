import os
import django
import sys
from unittest.mock import patch, MagicMock
from django.test import TestCase
from tickets.management.commands.fetch_emails import Command
from tickets.models import Ticket, User, Department, Response
from email import message_from_bytes
from django.utils.timezone import now, timedelta
from django.core import mail
from django.contrib.auth import get_user_model

# Setup Django environment

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "query_hub.settings")
django.setup()


class FetchEmailsTest(TestCase):
    
    def setUp(self):
        """Set up test data before each test."""
        self.command = Command()
        self.sender_email = "student@wukong.com"
        self.subject = "Test Ticket Subject"
        self.body = "This is a test ticket body."
        self.department = Department.objects.create(name="general_enquiry")
        # Create or get a user for the student
        User = get_user_model()

        user, created = User.objects.get_or_create(
            username="@" + self.sender_email.split("@")[0],
            defaults={"email": self.sender_email, "password": "Password123"}
        )
        self.user = user
        if not created:
            print(f"⚠️ User {user.username} already exists.")
        
        self.existing_ticket = Ticket.objects.create(
            title="Test Ticket Subject",
            creator=self.user,  # ✅ Assign user correctly
            description="Test description",
            assigned_department=self.department,
            status="open"
        )       
    
    def tearDown(self):
        """Deletes all Tickets and Users after each test"""
        Ticket.objects.all().delete()
        User.objects.all().delete()
        Department.objects.all().delete()
        print("🧹 Deleted all tickets and users after test")

    """Test the fetch_emails command with mocked IMAP server"""

    @patch("tickets.management.commands.fetch_emails.imaplib.IMAP4_SSL")
    @patch("tickets.management.commands.fetch_emails.send_mail")  # Mock send_mail
    
    def test_fetch_emails_sends_confirmation(self, mock_send_mail, mock_imap):
        """Test if the fetch_emails command sends a confirmation email"""
      
        Ticket.objects.all().delete()
        
        # 1️⃣ Mock IMAP Sever
        mock_mail = MagicMock()
        mock_imap.return_value = mock_mail

        # 2️⃣ Mock IMAP Commands
        mock_mail.search.return_value = ("OK", [b"1"])  # Only one email
        mock_mail.fetch.return_value = ("OK", [(b"1", (b"Fake Email Content"))])  # Mock email content

        # 3️⃣ Mock Email Content
        fake_email_bytes = b"From: student1@wukong.com\nSubject: Help Needed\n\nThis is a test email."
        fake_email_msg = message_from_bytes(fake_email_bytes)  # Make sure it's a valid email message
        mock_mail.fetch.return_value = ("OK", [(b"1", fake_email_msg.as_bytes())])

        # 4️⃣ Run the fetch_emails command
        command = Command()
        command.handle()

        # 5️⃣ Check if a Ticket is created
        ticket = Ticket.objects.first()
        self.assertIsNotNone(ticket, "❌ Ticket not created")
        self.assertEqual(ticket.title, "Help Needed")

        # 6️⃣ Check if send_mail is called
        mock_send_mail.assert_called_once()
        args, kwargs = mock_send_mail.call_args

        # 7️⃣ Check if the email is sent to the student
        self.assertIn("student1@wukong.com", kwargs.get("recipient_list"))

        # 8️⃣ Check if the email content is correct
        self.assertIn("WuKong Help Desk", kwargs.get("html_message"))
        self.assertIn("Your Ticket Has Been Received", kwargs.get("html_message"))

        print("✅ Test fetch_emails sends a confirmation email")
        
        

    def test_duplicate_ticket_with_response(self):
        """Test that duplicate tickets are rejected if a response exists."""
        
        # Create an existing ticket
        existing_ticket = Ticket.objects.create(
            title=self.subject,
            description=self.body,
            creator=self.user,
            sender_email=self.sender_email,
            status="open",
            assigned_department=self.department,
            created_at=now() - timedelta(days=3)  # Within 7 days
        )
        
        existing_ticket = Ticket.objects.filter(title=self.subject).first()
        self.assertIsNotNone(existing_ticket, "❌ existing_ticket should not be None before adding answers.")

        Response.objects.create(  # Ensure it exists before calling .create()
            ticket=existing_ticket,
            responder=self.user,
            content="This is a response from the officer.",
            created_at=now() - timedelta(days=2)
        )
        
        self.assertTrue(existing_ticket.responses.exists(), "❌ The existing ticket has no responses, duplicate check will fail!")

        # Check if duplicate detection works
        duplicate_ticket = self.command.is_duplicate_ticket(self.sender_email, self.subject, self.body)
        
        self.assertIsNotNone(duplicate_ticket)  # Should detect duplicate
        self.assertEqual(duplicate_ticket.id, existing_ticket.id)  # Should return the same ticket

    def test_duplicate_ticket_without_response_after_7_days(self):
        """Test that a ticket can be resubmitted if no response after 7 days."""
        
        # Create an old ticket without response
        Ticket.objects.create(
            title=self.subject,
            description=self.body,
            creator=self.user,
            sender_email=self.sender_email,
            status="open",
            assigned_department=self.department,
            created_at=now() - timedelta(days=8)  # Older than 7 days
        )

        # Check if the function allows ticket creation
        duplicate_ticket = self.command.is_duplicate_ticket(self.sender_email, self.subject, self.body)
        
        self.assertIsNone(duplicate_ticket)  # Should NOT detect a duplicate, allowing resubmission

    def test_duplicate_ticket_email_notification(self):
        """Test that a duplicate ticket sends a notification email."""
        
        # Create a recent duplicate ticket
        existing_ticket = Ticket.objects.create(
            title=self.subject,
            description=self.body,
            creator=self.user,
            sender_email=self.sender_email,
            status="open",
            assigned_department=self.department,
            created_at=now() - timedelta(days=3)  # Within 7 days
        )

        # Call the function to send an email
        self.command.send_duplicate_notice(self.sender_email, self.subject, existing_ticket.id)

        # Verify an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Duplicate Ticket Submission", mail.outbox[0].subject)
        self.assertIn("You have already submitted a ticket", mail.outbox[0].body)
        self.assertIn(str(existing_ticket.id), mail.outbox[0].body)

    
