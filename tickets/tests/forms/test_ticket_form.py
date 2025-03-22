# tickets/tests/forms/test_ticket_form.py

from django.test import TestCase
from tickets.forms import TicketForm
from tickets.models import User

class TicketFormTestCase(TestCase):
    """Unit tests for the TicketForm."""

    def setUp(self):
        # Provide unique emails for each user to avoid IntegrityError
        self.student_user = User.objects.create_user(
            username='@student1',
            password='Password123',
            role='students',
            email='student1@example.com'  # must be unique
        )
        self.non_student_user = User.objects.create_user(
            username='@programofficer1',
            password='Password123',
            role='program_officers',
            email='programofficer1@example.com'  # must be unique
        )

        self.form_data = {
            'title': 'Test Title',
            'description': 'Test Description',
            'priority': 'high',
        }

    def test_student_cannot_set_priority(self):
        """
        If the user is a student, the form's __init__ should pop
        the 'priority' field, so it won't even exist.
        """
        form = TicketForm(user=self.student_user, data=self.form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        # Confirm 'priority' was removed
        self.assertNotIn('priority', form.fields, "Priority field should be removed for a student")

        ticket = form.save(commit=False)
        self.assertEqual(ticket.title, self.form_data['title'])
        self.assertEqual(ticket.description, self.form_data['description'])
        # Since priority is removed, the model might use the default priority or remain unchanged

    def test_non_student_can_set_priority(self):
        """
        If user is not a student, the 'priority' field remains.
        """
        form = TicketForm(user=self.non_student_user, data=self.form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertIn('priority', form.fields, "Priority field should remain for non-student")

        ticket = form.save(commit=False)
        self.assertEqual(ticket.title, self.form_data['title'])
        self.assertEqual(ticket.description, self.form_data['description'])
        self.assertEqual(ticket.priority, 'high', "Non-student can set priority to 'high'")

    def test_form_with_no_user_argument(self):
        """
        If 'user=None' is passed, the 'priority' field is not removed
        (no check for user.is_student()).
        """
        form = TicketForm(data=self.form_data)  # no 'user' argument
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertIn('priority', form.fields, "Priority field should remain if user=None")

        ticket = form.save(commit=False)
        self.assertEqual(ticket.title, self.form_data['title'])
        self.assertEqual(ticket.description, self.form_data['description'])
        self.assertEqual(ticket.priority, 'high')
