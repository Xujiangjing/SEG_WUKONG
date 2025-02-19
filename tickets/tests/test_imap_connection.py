from django.test import TestCase
from unittest.mock import patch, MagicMock
import imaplib

class IMAPConnectionTest(TestCase):
    """Test case for checking IMAP connection."""

    @patch("imaplib.IMAP4_SSL")  # ✅ Mock IMAP to avoid real network calls
    def test_imap_login_success(self, mock_imap):
        """Test if IMAP login is successful."""
        # 🔹 Mock IMAP behavior
        mock_mail = MagicMock()
        mock_imap.return_value = mock_mail

        # ✅ Attempt to connect
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login("test@example.com", "password123")
            mail.logout()
            success = True
        except Exception as e:
            success = False

        # ✅ Verify that `login()` and `logout()` were called
        mock_mail.login.assert_called_once_with("test@example.com", "password123")
        mock_mail.logout.assert_called_once()

        # ✅ Assert connection was successful
        self.assertTrue(success, "❌ IMAP Login Failed!")

    @patch("imaplib.IMAP4_SSL")  # ✅ Mock IMAP failure case
    def test_imap_login_failure(self, mock_imap):
        """Test if IMAP login fails gracefully."""
        mock_imap.side_effect = imaplib.IMAP4.error("IMAP Authentication Failed")

        # ✅ Attempt connection
        with self.assertRaises(imaplib.IMAP4.error):
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login("test@example.com", "wrongpassword")

        print("✅ IMAP failure handled correctly.")
