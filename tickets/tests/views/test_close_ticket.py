from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models import Ticket, Department

User = get_user_model()

class CloseTicketViewTest(TestCase):

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

    def test_specialist_cannot_close_ticket(self):
        self.client.login(username="@janedoe", password="Password123")
        ticket1 = Ticket.objects.create(
            title="Test Ticket1",
            creator=self.student_user,
            status="open",
            assigned_user=self.specialist_user,
            assigned_department=self.department.name
        )
        response = self.client.get(reverse('close_ticket', args=[ticket1.id]))
        ticket1.refresh_from_db()
        self.assertEqual(ticket1.status, 'open')
        self.assertRedirects(response, reverse('dashboard'))
    
    def test_program_officer_cannot_close_ticket(self):
        self.client.login(username="@janedoe", password="Password123")
        ticket2 = Ticket.objects.create(
            title="Test Ticket1",
            creator=self.student_user,
            status="open",
            assigned_user=self.specialist_user,
            assigned_department=self.department.name
        )
        response = self.client.get(reverse('close_ticket', args=[ticket2.id]))
        ticket2.refresh_from_db()
        self.assertEqual(ticket2.status, 'open')
        self.assertRedirects(response, reverse('dashboard'))


    def test_student_can_close_own_ticket(self):
        self.client.login(username="@johndoe", password="Password123")
        response = self.client.get(reverse('close_ticket', args=[self.ticket.id]))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'closed')
        self.assertRedirects(response, reverse('dashboard'))

    def test_student_cannot_close_other_ticket(self):
        other_student_user = User.objects.create_user(
            username="@otherstudentuser",
            first_name="Other",
            last_name="Student",
            email="otherstudentuser@example.com",
            role="students",
            password="Password123"
        )
        ticket3 = Ticket.objects.create(
            title="Test Ticket1",
            creator=self.student_user,
            status="open",
            assigned_user=self.specialist_user,
            assigned_department=self.department.name
        )
        self.client.login(username="@otherstudentuser", password="Password123")
        response = self.client.get(reverse('close_ticket', args=[ticket3.id]))
        ticket3.refresh_from_db()
        self.assertEqual(ticket3.status, 'open')
        self.assertRedirects(response, reverse('dashboard'))
