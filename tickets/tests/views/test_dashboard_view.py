from django.test import TestCase, RequestFactory
from django.urls import reverse
from unittest.mock import patch, MagicMock

# Import the view functions to be tested
from tickets.views import dashboard


# A simple FakeUser class to simulate users with different roles
class FakeUser:
    def __init__(self, role=None):
        self.role = role
        self.is_authenticated = True

    def is_program_officer(self):
        return self.role == "program_officer"

    def is_student(self):
        return self.role == "student"

    def is_specialist(self):
        return self.role == "specialist"


class DashboardViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    # Test dashboard_redirect to ensure it redirects to the correct dashboard
    # based on the user's role.
    def test_dashboard_redirect_program_officer(self):
        request = self.factory.get("/dashboard/")
        request.user = FakeUser("program_officer")
        response = dashboard.dashboard_redirect(request)
        # Check redirect status code and final URL
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard_program_officer"))

    def test_dashboard_redirect_student(self):
        request = self.factory.get("/dashboard/")
        request.user = FakeUser("student")
        response = dashboard.dashboard_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard_student"))

    def test_dashboard_redirect_specialist(self):
        request = self.factory.get("/dashboard/")
        request.user = FakeUser("specialist")
        response = dashboard.dashboard_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard_specialist"))

    def test_dashboard_redirect_no_role(self):
        # If the user has no role, redirect to the home page
        request = self.factory.get("/dashboard/")
        request.user = FakeUser()  # role is None
        response = dashboard.dashboard_redirect(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("home"))

    # Test student_dashboard
    @patch("tickets.views.dashboard.get_filtered_tickets")
    def test_student_dashboard(self, mock_get_filtered_tickets):
        dummy_tickets = ["ticket1", "ticket2"]
        mock_get_filtered_tickets.return_value = dummy_tickets
        # Simulate GET parameters in the request
        request = self.factory.get("/dashboard/dashboard_student/?search=test&status=open&sort=date")
        request.user = FakeUser("student")

        # Call the view, then render the response to check context_data and template_name
        response = dashboard.student_dashboard(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        self.assertIn("dashboard/dashboard_student.html", response.template_name)
        self.assertEqual(response.context_data.get("student_tickets"), dummy_tickets)
        mock_get_filtered_tickets.assert_called_once()

    # Test program_officer_dashboard
    @patch("tickets.views.dashboard.get_filtered_tickets")
    def test_program_officer_dashboard(self, mock_get_filtered_tickets):
        dummy_tickets = ["ticketA", "ticketB"]
        mock_get_filtered_tickets.return_value = dummy_tickets
        request = self.factory.get("/dashboard/dashboard_program_officer/?search=test&status=open&sort=date")
        request.user = FakeUser("program_officer")

        response = dashboard.program_officer_dashboard(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        self.assertIn("dashboard/dashboard_program_officer.html", response.template_name)
        self.assertEqual(response.context_data.get("all_tickets"), dummy_tickets)
        mock_get_filtered_tickets.assert_called_once()

    # Test specialist_dashboard
    @patch("tickets.views.dashboard.get_filtered_tickets")
    def test_specialist_dashboard(self, mock_get_filtered_tickets):
        dummy_tickets = ["ticketX", "ticketY"]
        mock_get_filtered_tickets.return_value = dummy_tickets
        request = self.factory.get("/dashboard/dashboard_specialist/?search=test&status=open&sort=date")
        request.user = FakeUser("specialist")

        response = dashboard.specialist_dashboard(request)
        response.render()

        self.assertEqual(response.status_code, 200)
        self.assertIn("dashboard/dashboard_specialist.html", response.template_name)
        self.assertEqual(response.context_data.get("assigned_tickets"), dummy_tickets)
        mock_get_filtered_tickets.assert_called_once()

    # Test visualize_ticket_data
    def test_visualize_ticket_data(self):
        dummy_reports = ["report1", "report2"]
        # Create a mock queryset whose order_by method returns dummy_reports
        mock_queryset = MagicMock()
        mock_queryset.order_by.return_value = dummy_reports

        # Use patch to replace DailyTicketClosureReport.objects.all
        with patch("tickets.views.dashboard.DailyTicketClosureReport.objects.all", return_value=mock_queryset):
            request = self.factory.get("/visualize_ticket_data/")
            request.user = FakeUser("student")
            response = dashboard.visualize_ticket_data(request)
            response.render()

            self.assertEqual(response.status_code, 200)
            self.assertIn("visualize_ticket_data.html", response.template_name)
            self.assertEqual(response.context_data.get("reports"), dummy_reports)