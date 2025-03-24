from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib import messages
from tickets.models import Ticket, TicketActivity, TicketAttachment, Department
from django.contrib.messages import get_messages

User = get_user_model()


class TicketDetailViewTestCase(TestCase):
    fixtures = [
        "tickets/tests/fixtures/default_user.json",
        "tickets/tests/fixtures/other_users.json",
    ]

    def setUp(self):
        self.department = Department.objects.create(
            name="welfare",
            description="txt",
        )
        self.specialist = User.objects.get(username="@peterpickles")
        self.specialist.role = "specialist"
        self.specialist.save()

        self.program_officer = User.objects.get(username="@janedoe")
        self.program_officer.role = "program_officer"
        self.program_officer.save()

        self.student = User.objects.get(username="@johndoe")
        self.student.role = "student"
        self.student.save()

        self.ticket = Ticket.objects.create(
            title="Test Ticket",
            creator=self.student,
            status="in_progress",
            assigned_user=self.specialist,
            assigned_department=self.department.name,
        )
        self.url = reverse("ticket_detail", kwargs={"ticket_id": self.ticket.id})

    def test_ticket_detail_view_as_creator(self):
        self.client.login(username="@johndoe", password="Password123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tickets/ticket_detail.html")
        self.assertContains(response, self.ticket.title)

    def test_ticket_detail_view_as_assigned_user(self):
        self.client.login(username="@peterpickles", password="Password123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tickets/ticket_detail.html")
        self.assertContains(response, self.ticket.title)

    def test_ticket_detail_view_as_program_officer(self):
        ticket = Ticket.objects.create(
            title="Test Ticket",
            creator=self.student,
            status="in_progress",
            assigned_user=self.program_officer,
            assigned_department=self.department.name,
        )
        self.client.login(username="@janedoe", password="Password123")
        url = reverse("ticket_detail", kwargs={"ticket_id": ticket.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tickets/ticket_detail.html")
        self.assertContains(response, "Test Ticket")

    def test_ticket_detail_view_as_other_user(self):
        other_user = User.objects.create_user(
            username="@otheruser",
            first_name="Other",
            last_name="User",
            email="otheruser@example.com",
            role="others",
            password="Password123",
        )
        self.client.login(username="@otheruser", password="Password123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    def test_ticket_detail_view_with_attachments(self):
        self.client.login(username="@johndoe", password="Password123")
        attachment = TicketAttachment.objects.create(
            ticket=self.ticket, file="test_file.txt"
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tickets/ticket_detail.html")
        self.assertContains(response, attachment.file)

    def test_ticket_detail_view_with_activities(self):
        self.client.login(username="@johndoe", password="Password123")
        activity = TicketActivity.objects.create(
            ticket=self.ticket, action="created", action_by=self.student
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tickets/ticket_detail.html")
        self.assertContains(response, activity.get_action_display())

    def test_ticket_detail_view_with_staff_warning(self):
        self.client.login(username="@janedoe", password="Password123")
        ticket = Ticket.objects.create(
            title="Staff Warning Ticket",
            creator=self.student,
            status="in_progress",
            return_reason="Please resubmit your transcript.",
            assigned_user=self.program_officer,
            assigned_department="general_enquiry",
        )
        url = reverse("ticket_detail", kwargs={"ticket_id": ticket.id})
        response = self.client.get(url)

        messages_list = list(get_messages(response.wsgi_request))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(messages_list), 1)
        self.assertIn(
            "This ticket is waiting for the student to update.", str(messages_list[0])
        )
