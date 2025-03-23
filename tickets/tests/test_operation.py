from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from tickets.forms import ReturnTicketForm
from tickets.models import (DailyTicketClosureReport, Department, Ticket,
                            TicketActivity, User)


class TicketViewTestCase(TestCase):
    fixtures = ['tickets/tests/fixtures/default_user.json']

    def setUp(self):
        self.department = Department.objects.create(name='it_support', description='IT Support')

        self.student = User.objects.create_user(
            username='@student', password='Password123', role='students',
            email='student@example.com', first_name='Student', last_name='One'
        )
        self.student.department = self.department
        self.student.save()

        self.specialist = User.objects.create_user(
            username='@specialist', password='Password123', role='specialists',
            email='specialist@example.com', first_name='Specialist', last_name='One'
        )
        self.specialist.department = self.department
        self.specialist.save()

        self.ticket = Ticket.objects.create(
            creator=self.student,
            title="Test Ticket",
            description="This is a test ticket.",
            assigned_department=self.department.name,
            assigned_user=self.specialist,
            status="in_progress"
        )
    def test_return_ticket_by_specialist(self):
        self.client.login(username='@specialist', password='Password123')
        url = reverse('return_ticket', kwargs={'ticket_id': self.ticket.id})
        response = self.client.post(url, {'return_reason': 'Need more details'})
        
        self.ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.status, "in_progress")
        self.assertEqual(self.ticket.return_reason, "Need more details")
        self.assertFalse(self.ticket.can_be_managed_by_specialist)
        self.assertFalse(self.ticket.can_be_managed_by_program_officers)
        self.assertTrue(self.ticket.need_student_update)
        
        activity = TicketActivity.objects.filter(ticket=self.ticket, action='Returned').first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.action_by, self.specialist)
        self.assertEqual(activity.comment, f"Return to student : {self.student.full_name()}")
        
    def test_close_ticket_by_student(self):
        self.client.login(username='@student', password='Password123')
        url = reverse('close_ticket', kwargs={'ticket_id': self.ticket.id})
        response = self.client.post(url)
        
        self.ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.status, "closed")
        self.assertFalse(self.ticket.can_be_managed_by_program_officers)
        self.assertFalse(self.ticket.can_be_managed_by_specialist)
        self.assertTrue(self.ticket.program_officer_resolved)
        self.assertTrue(self.ticket.specialist_resolved)
        
        activity = TicketActivity.objects.filter(ticket=self.ticket, action='closed_manually').first()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.action_by, self.student)
        self.assertEqual(activity.comment, "Ticket closed manually by the student.")
        
        report = DailyTicketClosureReport.objects.filter(date=timezone.now().date(), department=self.department.name).first()
        self.assertIsNotNone(report)
        self.assertGreaterEqual(report.closed_manually, 1)
        
    def test_close_ticket_by_specailist(self):
        self.client.login(username='@specialist', password='Password123')
        url = reverse('close_ticket', kwargs={'ticket_id': self.ticket.id})
        response = self.client.post(url)
        self.ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
    def test_by_specialist(self):
        self.client.login(username='@specialist', password='Password123')
        url = reverse('return_ticket', kwargs={'ticket_id': self.ticket.id})
        self.ticket.status = 'closed'
        self.ticket.save()
        response = self.client.post(url)
        self.ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
    def test_close_ticket_by_student_without_form(self):
        self.client.login(username='@student', password='Password123')
        url = reverse('close_ticket', kwargs={'ticket_id': self.ticket.id})
        response = self.client.post(url)
        self.ticket.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        
    @patch('tickets.models.DailyTicketClosureReport.objects.get_or_create', side_effect=Exception("Database error"))
    def test_close_ticket_report_creation_failure(self, mock_get_or_create):
        self.client.login(username='@student', password='Password123')
        url = reverse('close_ticket', kwargs={'ticket_id': self.ticket.id})

        # with self.assertRaises(Exception) as context:
        response = self.client.post(url, {'return_reason': 'System error test'})
        self.assertEqual(response.status_code, 302)
