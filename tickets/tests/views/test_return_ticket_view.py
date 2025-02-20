import uuid

from django.test import TestCase
from django.urls import reverse
from tickets.models import Department, Ticket, User


class ReturnTicketViewTestCase(TestCase):
    """Tests for the return ticket view."""

    fixtures = [
        'tickets/tests/fixtures/default_user.json',
        'tickets/tests/fixtures/other_users.json'
    ]

    def setUp(self):
        self.department = Department.objects.create(
            name="welfare",
            description="txt",
        )
        self.specialist_user = User.objects.get(username='@peterpickles')
        self.student_user = User.objects.get(username='@johndoe')
        self.program_officer_user = User.objects.get(username='@johndoe')
        self.ticket = Ticket.objects.create(
            title="Test Ticket",
            creator=self.student_user,
            status="open",
            assigned_user=self.specialist_user,
            assigned_department=self.department.name
        )

    def test_program_officer_can_return_ticket(self):
        self.client.login(username="@janedoe", password="Password123")
        response = self.client.post(
            reverse("return_ticket", args=[self.ticket.pk]),
            {"return_reason": "Missing details"}
        )
        self.ticket.refresh_from_db()

        self.assertEqual(self.ticket.status, "returned")
        self.assertEqual(self.ticket.return_reason, "Missing details")
        self.assertRedirects(response, reverse("ticket_list"))

    def test_specialist_cannot_return_ticket(self):
        self.client.login(username="@peterpickles", password="Password123")
        response = self.client.post(
            reverse("return_ticket", args=[self.ticket.pk]),
            {"return_reason": "Missing details"}
        )
        self.ticket.refresh_from_db()

        self.assertEqual(self.ticket.status, "open")
        self.assertIsNone(self.ticket.return_reason)
        self.assertRedirects(response, reverse("ticket_list"))

    def test_cannot_return_twice(self):
        self.client.login(username="@janedoe", password="Password123")
        self.client.post(
            reverse("return_ticket", args=[self.ticket.pk]),
            {"return_reason": "Missing details"}
        )
        response = self.client.post(
            reverse("return_ticket", args=[self.ticket.pk]),
            {"return_reason": "Missing details"}
        )
        self.ticket.refresh_from_db()

        self.assertEqual(self.ticket.status, "returned")
        self.assertEqual(self.ticket.return_reason, "Missing details")
        self.assertRedirects(response, reverse("ticket_list"))

    def test_get_request(self):
        self.client.login(username="@janedoe", password="Password123")
        response = self.client.get(reverse("return_ticket", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "open")

    def test_not_found(self):
        self.client.login(username="@janedoe", password="Password123")
        fake_uuid = uuid.uuid4()  # A UUID that doesn't exist
        response = self.client.post(
            reverse("return_ticket", args=[fake_uuid]),
            {"return_reason": "Missing details"}
        )
        self.assertEqual(response.status_code, 404)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "open")

    def test_form_invalid(self):
        self.client.login(username="@janedoe", password="Password123")
        response = self.client.post(
            reverse("return_ticket", args=[self.ticket.pk]),
            {"return_reason": ""}
        )
        self.ticket.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ticket.status, "open")
        self.assertIsNone(self.ticket.return_reason)
        self.assertContains(response, "This field is required.")