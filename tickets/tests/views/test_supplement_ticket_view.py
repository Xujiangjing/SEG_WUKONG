import uuid

from django.test import TestCase
from django.urls import reverse
from tickets.models import Department, Ticket, User

class SupplementTicketViewTestCase(TestCase):
    """Tests for the supplement ticket view."""

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
        self.student2 = User.objects.get(username='@petrapickles')
        self.ticket = Ticket.objects.create(
            title="Test Ticket",
            creator=self.student_user,
            status="returned",
            assigned_user=self.specialist_user,
            assigned_department=self.department.name
        )

    def test_program_officer_cannot_supplement_ticket(self):
        self.client.login(username="@janedoe", password="Password123")
        response = self.client.post(
            reverse('supplement_ticket', args=[self.ticket.pk]),
            {'supplement_info': 'Supplemental information'}
        )

        self.assertRedirects(response, reverse('dashboard'))

    def test_student_can_supplement_own_ticket(self):
        self.client.login(username="@johndoe", password="Password123")
        response = self.client.post(
            reverse('supplement_ticket', args=[self.ticket.pk]),
            {'supplement_info': 'Supplemental information'}
        )
        self.ticket.refresh_from_db()

        self.assertEqual(self.ticket.status, 'open')
        self.assertRedirects(response, reverse('dashboard'))

    def test_get_request(self):
        self.client.login(username="@johndoe", password="Password123")
        response = self.client.get(reverse('supplement_ticket', args=[self.ticket.pk]))
        self.ticket.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ticket.status, 'returned')

    def test_not_found(self):
        self.client.login(username="@janedoe", password="Password123")
        fake_uuid = uuid.uuid4()  # A UUID that doesn't exist
        response = self.client.post(
            reverse("supplement_ticket", args=[fake_uuid]),
            {"supplement_info": "Supplemental information"}
        )
        self.assertEqual(response.status_code, 404)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "returned")

    def test_not_own_ticket(self):
        self.client.login(username="@petrapickles", password="Password123")
        response = self.client.post(
            reverse("supplement_ticket", args=[self.ticket.pk]),
            {"supplement_info": "Supplemental information"}
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "returned")
        self.assertRedirects(response, reverse('dashboard'))

    def test_form_invalid(self):
        self.client.login(username="@johndoe", password="Password123")
        response = self.client.post(
            reverse("supplement_ticket", args=[self.ticket.pk]),
            {"supplement_info": ""}
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "returned")
        self.assertContains(response, "This field is required.")
        self.assertTemplateUsed(response, "tickets/supplement_ticket.html")