from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from tickets.models import Ticket, DailyTicketClosureReport
from django.contrib.auth import get_user_model

from tickets.views.dashboard import (
    dashboard_redirect,
    student_dashboard,
    program_officer_dashboard,
    specialist_dashboard,
    visualize_ticket_data,
)

User = get_user_model()

class DashboardViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()

        # Create users
        self.student_user = User.objects.create_user(username="student", email="student@example.com", password="test")
        self.student_user.is_student = lambda: True
        self.student_user.is_program_officer = lambda: False
        self.student_user.is_specialist = lambda: False

        self.officer_user = User.objects.create_user(username="officer", email="officer@example.com", password="test")
        self.officer_user.is_student = lambda: False
        self.officer_user.is_program_officer = lambda: True
        self.officer_user.is_specialist = lambda: False

        self.specialist_user = User.objects.create_user(username="specialist", email="specialist@example.com", password="test")
        self.specialist_user.is_student = lambda: False
        self.specialist_user.is_program_officer = lambda: False
        self.specialist_user.is_specialist = lambda: True

        self.generic_user = User.objects.create_user(username="generic", email="generic@example.com", password="test")
        self.generic_user.is_student = lambda: False
        self.generic_user.is_program_officer = lambda: False
        self.generic_user.is_specialist = lambda: False

    def test_redirect_student_dashboard(self):
        request = self.factory.get("/dashboard/")
        request.user = self.student_user
        response = dashboard_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard_student"))

    def test_redirect_officer_dashboard(self):
        request = self.factory.get("/dashboard/")
        request.user = self.officer_user
        response = dashboard_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard_program_officer"))

    def test_redirect_specialist_dashboard(self):
        request = self.factory.get("/dashboard/")
        request.user = self.specialist_user
        response = dashboard_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard_specialist"))

    def test_redirect_generic_dashboard(self):
        request = self.factory.get("/dashboard/")
        request.user = self.generic_user
        response = dashboard_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("home"))

    def test_student_dashboard_view(self):
        self.client.force_login(self.student_user)
        Ticket.objects.create(title="Student Ticket", creator=self.student_user)
        response = self.client.get(reverse("dashboard_student"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("student_tickets", response.context)

    def test_program_officer_dashboard_view(self):
        self.client.force_login(self.officer_user)
        Ticket.objects.create(title="Unanswered Ticket", creator=self.student_user)
        response = self.client.get(reverse("dashboard_program_officer"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("all_tickets", response.context)

    def test_specialist_dashboard_view(self):
        self.client.force_login(self.specialist_user)
        Ticket.objects.create(title="Specialist Ticket", assigned_user=self.specialist_user, creator=self.specialist_user)
        response = self.client.get(reverse("dashboard_specialist"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("assigned_tickets", response.context)

    def test_visualize_ticket_data_view(self):
        self.client.force_login(self.officer_user)
        DailyTicketClosureReport.objects.create(date="2025-03-01",department="IT",closed_by_inactivity=3,closed_manually=2,in_progress=1)
        response = self.client.get(reverse("visualize_ticket_data"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("reports", response.context)