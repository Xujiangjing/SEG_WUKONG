from django.test import TestCase
from unittest.mock import patch, MagicMock
import smtplib

class SMTPConnectionTest(TestCase):
    """Test case for checking SMTP connection."""

    @patch("smtplib.SMTP")  # Mock SMTP to avoid real network calls
    def test_smtp_connection_success(self, mock_smtp):
        """Test if SMTP connection is successful."""
        # Mock SMTP behavior
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        # Attempt to connect
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login("test@wukong.ac.uk", "password123")
            server.quit()
            success = True
        except Exception as e:
            success = False

        # Verify that `starttls()`, `login()`, and `quit()` were called
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@wukong.ac.uk", "password123")
        mock_server.quit.assert_called_once()

        # Assert connection was successful
        self.assertTrue(success, "SMTP Connection Failed!")

    @patch("smtplib.SMTP")  # Mock SMTP failure case
    def test_smtp_connection_failure(self, mock_smtp):
        """Test if SMTP connection fails gracefully."""
        mock_smtp.side_effect = smtplib.SMTPException("SMTP Error")

        # Attempt connection
        with self.assertRaises(smtplib.SMTPException):
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login("test@wukong.ac.uk", "wrongpassword")
            server.quit()

       
