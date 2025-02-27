import unittest
from unittest.mock import patch
from django.test import override_settings
from tickets.management.commands.fetch_emails import Command

class TestSpamDetection(unittest.TestCase):

    @override_settings(TESTING=False)
    @patch('tickets.management.commands.fetch_emails.requests.post')
    def test_is_spam_true(self, mock_post):
        """Test normal email detection (above 0.8)"""
        mock_post.return_value.json.return_value = {
            'attributeScores': {
                'SPAM': {
                    'summaryScore': {'value': 0.9}  # Above the threshold of 0.8
                }
            }
        }
        mock_post.return_value.status_code = 200

        command = Command()
        subject = "Win a free iPhone"
        body = "Click here to claim your prize"
        result = command.is_spam(subject, body)
        self.assertTrue(result)  # Expected to return True

    @override_settings(TESTING=False)
    @patch('tickets.management.commands.fetch_emails.requests.post')
    def test_is_spam_false(self, mock_post):
        """Test normal email detection (below 0.8)"""
        mock_post.return_value.json.return_value = {
            'attributeScores': {
                'SPAM': {
                    'summaryScore': {'value': 0.2}  # Below the threshold of 0.8
                }
            }
        }
        mock_post.return_value.status_code = 200

        command = Command()
        subject = "Meeting agenda"
        body = "Please find the attached agenda for tomorrow's meeting."
        result = command.is_spam(subject, body)
        self.assertFalse(result)  # Expected to return False

    @override_settings(TESTING=False)
    @patch('tickets.management.commands.fetch_emails.requests.post')
    def test_is_spam_api_failure(self, mock_post):
        """Test when the API returns an error"""
        mock_post.return_value.status_code = 500
        mock_post.return_value.json.return_value = {}  # Empty JSON response

        command = Command()
        subject = "Test subject"
        body = "Test body"
        result = command.is_spam(subject, body)
    
        self.assertFalse(result)  # Expected to return False

    @override_settings(TESTING=True)
    def test_is_spam_skipped_in_testing_mode(self):
        """Test when the command is run in testing mode"""
        command = Command()
        subject = "Test subject"
        body = "Test body"
        result = command.is_spam(subject, body)
        self.assertFalse(result)  # Expected to return False
    

if __name__ == '__main__':
    unittest.main()
