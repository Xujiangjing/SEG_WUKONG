from django.test import TestCase
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from tickets.models import (
    Department,
    User,
    Ticket,
    TicketAttachment,
    Response,
    AITicketProcessing,
    MergedTicket,
    DailyTicketClosureReport,
)


class ModelCoverageTestCase(TestCase):

    def setUp(self):
        # 1) Create a Department
        self.dept = Department.objects.create(
            name="health_services",
            description="Handles healthcare-related issues",
            responsible_roles="specialists"
        )

        # 2) Create a user (specialist) with first/last name so full_name() is not empty
        self.specialist = User.objects.create_user(
            username='@specialist_user',
            password='Password123',
            role='specialists',
            email='specialist@example.com',
            first_name='Speci',
            last_name='List',
            department=self.dept
        )

        # 3) Create another user (student)
        self.student = User.objects.create_user(
            username='@student_user',
            password='Password123',
            role='students',
            email='student@example.com'
        )

        # 4) Create a Ticket
        self.ticket = Ticket.objects.create(
            creator=self.student,
            title="Coverage Ticket",
            description="Check model coverage lines",
            status="in_progress",
            priority="urgent",
            assigned_department="health_services",
            assigned_user=self.specialist
        )

        # 5) Create a TicketAttachment
        fake_file = SimpleUploadedFile("example.doc", b"dummy content")
        self.attachment = TicketAttachment.objects.create(
            ticket=self.ticket,
            file=fake_file
        )

        self.response = Response.objects.create(
            ticket=self.ticket,
            responder=self.specialist,
            content="Response content for coverage test."
        )

        self.ai_ticket = AITicketProcessing.objects.create(
            ticket=self.ticket,
            ai_generated_response="AI generated coverage test",
            ai_assigned_department="health_services",
            ai_assigned_priority="urgent"
        )

        self.merged_ticket = MergedTicket.objects.create(
            primary_ticket=self.ticket
        )

        self.closure_report = DailyTicketClosureReport.objects.create(
            date=timezone.now().date(),
            department="health_services",
            closed_by_inactivity=1,
            closed_manually=2
        )

    def test_ticket_get_department_name(self):
        self.assertEqual(self.ticket.get_department_name(), "Health Services")

    def test_ticket_get_status_name(self):
        self.assertEqual(self.ticket.get_status_name(), "In Progress")

    def test_ticket_get_priority_name(self):
        self.assertEqual(self.ticket.get_priority_name(), "Urgent")

    def test_attachment_filename_property(self):

        self.assertIn("example.doc", self.attachment.filename)

    def test_response_str_with_responder(self):

        resp_str = str(self.response)
        # Should contain the response UUID, the ticket UUID, and 'Speci List'.
        self.assertIn(str(self.response.id), resp_str)
        self.assertIn(str(self.ticket.id), resp_str)
        self.assertIn(self.specialist.full_name(), resp_str)

    def test_response_str_no_responder(self):
        """Test Response.__str__ when responder=None => 'Unknown'."""
        response_no_responder = Response.objects.create(
            ticket=self.ticket,
            responder=None,
            content="No user for coverage"
        )
        resp_str = str(response_no_responder)
        self.assertIn("Unknown", resp_str)

    def test_ai_ticket_processing_str(self):
        """
        Test AITicketProcessing.__str__ => 'AI Processing for Ticket {ticket.id}'.
        """
        self.assertIn(
            f"AI Processing for Ticket {self.ticket.id}",
            str(self.ai_ticket)
        )

    def test_merged_ticket_str(self):
        """Test MergedTicket.__str__ => 'Merged into Ticket {primary_ticket.id}'."""
        merged_str = str(self.merged_ticket)
        self.assertIn(f"Merged into Ticket {self.ticket.id}", merged_str)

    def test_daily_ticket_closure_report_str(self):
        """
        Test DailyTicketClosureReport.__str__ => 'Report for {date} for {department}'.
        """
        report_str = str(self.closure_report)
        expected_date = str(self.closure_report.date)  # e.g. '2025-03-22'
        self.assertIn("Report for", report_str)
        self.assertIn(expected_date, report_str)
        self.assertIn("health_services", report_str)
