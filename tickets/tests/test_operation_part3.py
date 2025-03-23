from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from tickets.models import (DailyTicketClosureReport, Department, Ticket,
                            TicketActivity, User)


class TicketViewTests(TestCase):
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

    def test_update_ticket_success(self):
        self.client.login(username="@student", password="Password123")
        url = reverse("update_ticket", kwargs={"ticket_id": self.ticket.id})
        response = self.client.post(url, {"update_message": "New update information"})

        self.ticket.refresh_from_db()
        self.assertIn("New update information", self.ticket.description)
    #     self.assertEqual(self.ticket.status, "in_progress")

    #     activity = TicketActivity.objects.filter(ticket=self.ticket).first()
    #     self.assertIsNotNone(activity)
    #     self.assertEqual(activity.action, "status_updated")
    #     self.assertEqual(activity.comment, "New update information")

    #     self.assertRedirects(response, reverse("ticket_detail", kwargs={"ticket_id": self.ticket.id}))

    # def test_update_ticket_permission_denied(self):
    #     self.client.login(username="@specialist", password="Password123")
    #     url = reverse("update_ticket", kwargs={"ticket_id": self.ticket.id})
    #     response = self.client.post(url, {"update_message": "Unauthorized update"})

    #     self.ticket.refresh_from_db()
    #     self.assertNotIn("Unauthorized update", self.ticket.description)

    #     self.assertEqual(response.status_code, 302)

    # def test_manage_ticket_page_student(self):
    #     self.client.login(username="@student", password="Password123")
    #     url = reverse("manage_ticket_page", kwargs={"ticket_id": self.ticket.id})
    #     response = self.client.get(url)

    #     self.assertEqual(response.status_code, 200)
    #     self.assertTemplateUsed(response, "tickets/manage_tickets_page_for_student.html")
    #     self.assertIn("update_ticket", response.context["actions"])

    # def test_manage_ticket_page_specialist(self):
    #     self.client.login(username="@specialist", password="Password123")
    #     url = reverse("manage_ticket_page", kwargs={"ticket_id": self.ticket.id})
    #     response = self.client.get(url)

    #     self.assertEqual(response.status_code, 200)
    #     self.assertTemplateUsed(response, "tickets/manage_tickets_page_for_specialist.html")
    #     self.assertIn("respond_ticket", response.context["actions"])

