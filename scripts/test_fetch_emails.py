import os
import django
import sys
from unittest.mock import patch, MagicMock
from django.test import TestCase
from tickets.management.commands.fetch_emails import Command
from tickets.models import Ticket, User, Department
from email import message_from_bytes

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "query_hub.settings")
django.setup()

class FetchEmailsTest(TestCase):
    def setUp(self):
        """Create a Department for the Ticket"""
        Department.objects.create(name="general_enquiry")  
        
    """Test the fetch_emails command with mocked IMAP server"""

    @patch("tickets.management.commands.fetch_emails.imaplib.IMAP4_SSL")
    @patch("tickets.management.commands.fetch_emails.send_mail")  # Mock send_mail
    def test_fetch_emails_sends_confirmation(self, mock_send_mail, mock_imap):
        """Test if the fetch_emails command sends a confirmation email"""

        # 1️⃣ Mock IMAP Sever
        mock_mail = MagicMock()
        mock_imap.return_value = mock_mail

        # 2️⃣ Mock IMAP Commands
        mock_mail.search.return_value = ("OK", [b"1"])  # Only one email
        mock_mail.fetch.return_value = ("OK", [(b"1", (b"Fake Email Content"))])  # Mock email content

        # 3️⃣ Mock Email Content
        fake_email_bytes = b"From: student@example.com\nSubject: Help Needed\n\nThis is a test email."
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
        self.assertIn("student@example.com", kwargs.get("recipient_list"))

        # 8️⃣ Check if the email content is correct
        self.assertIn("WuKong Help Desk", kwargs.get("html_message"))
        self.assertIn("Your Ticket Has Been Received", kwargs.get("html_message"))

        print("✅ Test fetch_emails sends a confirmation email")
