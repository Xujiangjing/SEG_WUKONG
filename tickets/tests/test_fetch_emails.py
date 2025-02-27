import os
import django
import sys
from unittest.mock import patch, MagicMock
from tickets.management.commands.fetch_emails import Command
from tickets.models import Ticket, User, Department, Response
from email import message_from_bytes
from django.utils.timezone import now, timedelta
from django.core import mail
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TransactionTestCase

# Setup Django environment

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "query_hub.settings")
django.setup()

class FetchEmailsTest(TransactionTestCase):
    """Test the fetch_emails command"""

    def setUp(self):
        """Creates a Ticket and User before each test"""
        self.command = Command()
        self.sender_email = "student@wukong.ac.uk"
        self.subject = "Test Ticket Subject"
        self.body = "This is a test ticket body."

        with transaction.atomic():  
            self.department = Department.objects.create(name="general_enquiry")
            self.user = User.objects.create(email=self.sender_email.strip(), username="@student")
            self.existing_ticket = Ticket.objects.create(
                title=self.subject.strip(),
                description=self.body.strip(),
                creator=self.user,
                sender_email=self.sender_email.strip(),
                status="open",
                assigned_department=self.department,
                created_at=now() - timedelta(days=3)
            )
            self.response = Response.objects.create(
                ticket=self.existing_ticket,
                responder=self.user,
                content="This is a response from the officer.",
                created_at=now() - timedelta(days=2)
            )

        self.existing_ticket.refresh_from_db()
        
    def tearDown(self):
        """Deletes all Tickets and Users after each test"""
        Ticket.objects.all().delete()
        User = get_user_model()
        User.objects.all().delete()
        Department.objects.all().delete()
        Response.objects.all().delete()

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
        fake_email_bytes = b"From: student1@wukong.ac.uk\nSubject: Help Needed\n\nThis is a test email."
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
        self.assertIn("student1@wukong.ac.uk", kwargs.get("recipient_list"))

        # 8️⃣ Check if the email content is correct
        self.assertIn("WuKong Help Desk", kwargs.get("html_message"))
        self.assertIn("Your Ticket Has Been Received", kwargs.get("html_message"))

    def test_email_subject_decoding(self):
        """Test that the email subject is correctly decoded."""
        Ticket.objects.all().delete()
        encoded_subject = "=?utf-8?b?dGVzdCBzdWJqZWN0?="
        fake_email_bytes = f"From: student@wukong.ac.uk\nSubject: {encoded_subject}\n\nTest Body.".encode()
    
        fake_email_msg = message_from_bytes(fake_email_bytes)
    
        with patch("tickets.management.commands.fetch_emails.imaplib.IMAP4_SSL") as mock_imap:
            mock_mail = MagicMock()
            mock_imap.return_value = mock_mail
            mock_mail.search.return_value = ("OK", [b"1"])
            mock_mail.fetch.return_value = ("OK", [(b"1", fake_email_msg.as_bytes())])

            self.command.handle()
             
            ticket = Ticket.objects.first()
            self.assertIsNotNone(ticket)
            self.assertEqual(ticket.title, "test subject")
       
    def test_duplicate_ticket_with_response(self):
        """Test that a ticket with a response is detected as a duplicate."""
        if self.existing_ticket.responses.count() > 0:
            self.existing_ticket.status = "closed"
            self.existing_ticket.save()
            self.existing_ticket.refresh_from_db()
        
        duplicate_ticket = self.command.is_duplicate_ticket(
        self.sender_email,
        self.subject,
        self.body
        )
        
        self.assertIsNotNone(duplicate_ticket)  # Should detect a duplicate
        self.assertEqual(duplicate_ticket.id, self.existing_ticket.id, "❌ Duplicate ticket not detected")

    def test_duplicate_ticket_without_response_after_7_days(self):
        """Test that a ticket can be resubmitted if no response after 7 days."""
        old_created_at = now() - timedelta(days=8)

        with transaction.atomic():
            old_ticket = Ticket.objects.create(
                title=self.subject,
                description=self.body,
                creator=self.user,
                sender_email=self.sender_email,
                status="open",
                assigned_department=self.department.name
            )

        # Update the created_at date to 8 days ago
        Ticket.objects.filter(id=old_ticket.id).update(created_at=old_created_at)

        # Refresh the ticket
        old_ticket.refresh_from_db()
        # Ensure the ticket was created 8 days ago
        self.assertLess(old_ticket.created_at, now() - timedelta(days=7), "❌ created_at date is not 8 days ago")
        duplicate_ticket= self.command.is_duplicate_ticket(self.sender_email, self.subject, self.body)
        # Ensure the ticket can be resubmitted after 7 days without a response
        self.assertIsNone(duplicate_ticket, "❌ Duplicate ticket detected after 7 days")
        
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
        self.assertEqual(len(mail.outbox), 1, "❌ No email sent")
        
        sent_mail = mail.outbox[0]
        self.assertIn("Duplicate Ticket Submission", sent_mail.subject, "❌ Email subject is incorrect")

        self.assertIn("You have already submitted a ticket", sent_mail.body, "❌ Email body is incorrect")
        self.assertIn(str(existing_ticket.id), sent_mail.body, "❌ Ticket ID not found in email body")

    def test_skip_failure_notification(self):
        """Test that failure notification emails are skipped."""
        Ticket.objects.all().delete()
        fake_email_bytes = b"From: <mailer-daemon@server.com>\nSubject: Delivery Status Notification\n\nFailure report."
        fake_email_msg = message_from_bytes(fake_email_bytes)

        with patch("tickets.management.commands.fetch_emails.imaplib.IMAP4_SSL") as mock_imap:
            mock_mail = MagicMock()
            mock_imap.return_value = mock_mail
            mock_mail.search.return_value = ("OK", [b"1"])
            mock_mail.fetch.return_value = ("OK", [(b"1", fake_email_msg.as_bytes())])

            self.command.handle()

            # Ensure no ticket was created
            ticket = Ticket.objects.first()
            self.assertIsNone(ticket, "❌ Ticket created for failure notification")
     
    
