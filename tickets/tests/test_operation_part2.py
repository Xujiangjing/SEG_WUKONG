from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from tickets.models import (DailyTicketClosureReport, Department, Ticket,
                            TicketActivity, User)


class RedirectTicketViewTestCase(TestCase):
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

        self.officer = User.objects.create_user(
            username='@officer', password='Password123', role='program_officers',
            email='officer@example.com', first_name='Officer', last_name='One'
        )
        self.officer.department = self.department

        self.officer.save()
        self.ticket = Ticket.objects.create(
            creator=self.student,
            title="Test Ticket",
            description="This is a test ticket.",
            assigned_department=self.department.name,
            assigned_user=self.specialist,
            status="in_progress"
        )
        self.ticket.save()
        self.potential_ticket = Ticket.objects.create(
            creator=self.student,
            title="Potential Ticket",
            description="Test description for potential ticket",
            assigned_user=self.specialist,
            status="in_progress"
        )
        self.potential_ticket.save()

    def test_redirect_ticket_unauthenticated(self):
        url = reverse("redirect_ticket", kwargs={"ticket_id": self.ticket.id})
        response = self.client.post(url, {"new_assignee_id": "ai"})
        self.assertEqual(response.status_code, 302)

    def test_redirect_ticket_unauthorized(self):
        self.client.login(username="@student", password="Password123")
        url = reverse("redirect_ticket", kwargs={"ticket_id": self.ticket.id})
        response = self.client.post(url, {"new_assignee_id": "ai"})
        self.assertEqual(response.status_code, 403)
    
    def test_redirect_ticket_ai_assignment(self):
        self.client.login(username="@officer", password="Password123")
    #     url = reverse("redirect_ticket", kwargs={"ticket_id": self.ticket.id})

    #     response = self.client.post(url, {"new_assignee_id": "ai"})
    #     self.ticket.refresh_from_db()

    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(self.ticket.status, "in_progress")
    #     self.assertEqual(self.ticket.latest_action, "redirected")

    # def test_redirect_ticket_assign_specialist(self):
    #     self.client.login(username="@officer", password="Password123")
    #     url = reverse("redirect_ticket", kwargs={"ticket_id": self.ticket.id})

    #     response = self.client.post(url, {"new_assignee_id": self.specialist.id})
    #     self.ticket.refresh_from_db()

    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(self.ticket.assigned_user, self.specialist)
    #     self.assertEqual(self.ticket.status, "in_progress")
    #     self.assertEqual(self.ticket.latest_action, "redirected")

    # def test_redirect_ticket_invalid_specialist(self):
    #     self.client.login(username="@officer", password="Password123")
    #     url = reverse("redirect_ticket", kwargs={"ticket_id": self.ticket.id})

    #     response = self.client.post(url, {"new_assignee_id": 9999})
    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(response.json()["error"], "Selected specialist does not exist")

    # def test_redirect_ticket_missing_assignee(self):
    #     self.client.login(username="@officer", password="Password123")
    #     url = reverse("redirect_ticket", kwargs={"ticket_id": self.ticket.id})

    #     response = self.client.post(url, {})
    #     self.assertEqual(response.status_code, 400)
    #     self.assertEqual(response.json()["error"], "Selected specialist does not exist")


    # def test_respond_ticket(self):
    #     self.client.login(username='@officer', password='Password123')
    #     url = reverse('respond_ticket', kwargs={'ticket_id': self.ticket.id})
    #     response_message = "Test response"
    #     response = self.client.post(url, {'response_message': response_message})
    #     self.ticket.refresh_from_db()
    #     self.assertEqual(self.ticket.status, 'in_progress')
    #     activity = TicketActivity.objects.filter(ticket=self.ticket, action="responded").first()
    #     self.assertIsNotNone(activity)
    #     self.assertEqual(activity.comment, response_message)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertTemplateUsed(response, 'tickets/ticket_detail.html')
