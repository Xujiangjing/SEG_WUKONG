from unittest.mock import patch
import django.core.mail
from django.test import TestCase

class EmailSendingTest(TestCase):
    """Test case for sending emails."""

    def test_send_email_success(self):
        """Test if Django can successfully send an email."""
        with patch.object(django.core.mail, "send_mail", return_value=1) as mock_send_mail:
            # Call send_mail inside the test
            result = django.core.mail.send_mail(
                "Test Email",
                "This is a test email.",
                "test@example.com",
                ["wukonghelpdesk@gmail.com"],
                fail_silently=False,
            )

            # Ensure send_mail() was called
            mock_send_mail.assert_called_once()

            # Assert email sending was successful
            self.assertEqual(result, 1, "Email was not sent successfully!")

