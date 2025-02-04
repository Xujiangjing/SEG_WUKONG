from django.db.models import Count
from django.test import TestCase
from django.urls import reverse
from tickets.models import Department, Ticket, User


class DashboardViewTestCase(TestCase):
    """Tests for the dashboard view."""

    fixtures = ['tickets/tests/fixtures/default_user.json']  # Optional: provide a fixture if needed

    def setUp(self):
        # Creating the necessary data
        self.department = Department.objects.create(name='it_support', description='IT Support')

        self.program_officer = User.objects.create_user(
            username='@programofficer', password='Password123', role='program_officers',
            email= '111@qq.com', first_name='Program', last_name='Officer'
        )
        self.program_officer.department = self.department
        self.program_officer.save()

        self.student = User.objects.create_user(
            username='@student', password='Password123', role='students',
            email= '222@qq.com', first_name='Student', last_name='Student'
        )

        self.student.department = self.department
        self.student.save()
        
        self.specialist = User.objects.create_user(
            username='@specialist', password='Password123', role='specialists',
            email = '333.qq.com', first_name='Specialist', last_name='One'
        )
        self.specialist.department = self.department
        self.specialist.save()

        # Create a ticket assigned to the department
        self.ticket = Ticket.objects.create(
            creator=self.student,
            title="Test Ticket",
            description="This is a test ticket.",
            assigned_department=self.department.name,
            assigned_to=self.specialist
        )

        self.url = reverse('dashboard')

    def test_dashboard_for_program_officer_with_department(self):
        """Test dashboard for program officer with department."""
        self.client.login(username='@programofficer', password='Password123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertIn('department_tickets', response.context)
        self.assertIn('other_department_tickets', response.context)
        self.assertIn('ticket_stats', response.context)

    def test_dashboard_for_program_officer_without_department(self):
        """Test dashboard for program officer without department."""
        self.program_officer.department = None
        self.program_officer.save()
        self.client.login(username='@programofficer', password='Password123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertIn('department_tickets', response.context)
        self.assertIn('other_department_tickets', response.context)

    def test_dashboard_for_student(self):
        """Test dashboard for student."""
        self.client.login(username='@student', password='Password123')
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')
        self.assertIn('student_tickets', response.context)

    # def test_dashboard_for_specialist(self):
    #     """Test dashboard for specialist."""
    #     self.client.login(username='@specialist', password='Password123')
    #     response = self.client.get(self.url)

    #     self.assertEqual(response.status_code, 200)
    #     self.assertTemplateUsed(response, 'dashboard.html')
    #     self.assertIn('assigned_tickets', response.context)

    # def test_dashboard_for_unauthorized_user(self):
    #     """Test dashboard for unauthorized user (no specific role)."""
    #     user = User.objects.create_user(
    #         username='@unauthorized', password='Password123', role='others'
    #     )
    #     self.client.login(username='@unauthorized', password='Password123')
    #     response = self.client.get(self.url)

    #     self.assertEqual(response.status_code, 200)
    #     self.assertTemplateUsed(response, 'dashboard.html')
    #     self.assertIn('message', response.context)
    #     self.assertEqual(response.context['message'], "You do not have permission to view this dashboard.")

