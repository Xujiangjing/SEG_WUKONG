from django.test import TestCase
from unittest.mock import patch
from botocore.exceptions import ClientError
from tickets.models import Ticket, AITicketProcessing, MergedTicket
from tickets.ai_service import (
    classify_department,
    predict_priority,
    generate_ai_answer,
    ai_process_ticket,
    find_potential_tickets_to_merge,
    query_bedrock,
)

class AITicketProcessingTests(TestCase):

    def setUp(self):
        # Create a ticket to test with
        self.ticket = Ticket.objects.create(
            title="Test Ticket",
            description="I need help with my course registration.",
            status="in_progress",
        )
        # Create a ticket in the same department to be fetched later
        self.ticket_2 = Ticket.objects.create(
            title="Second Ticket",
            description="Another issue related to course registration.",
            status="in_progress",
        )
        # Create a ticket in a different department to ensure it's excluded
        self.ticket_3 = Ticket.objects.create(
            title="Third Ticket",
            description="An issue related to IT Support.",
            status="in_progress",
        )
        # Create AITicketProcessing entries for the tickets
        AITicketProcessing.objects.create(ticket=self.ticket, ai_assigned_department="academic_support")
        AITicketProcessing.objects.create(ticket=self.ticket_2, ai_assigned_department="academic_support")
        AITicketProcessing.objects.create(ticket=self.ticket_3, ai_assigned_department="it_support")

    @patch("tickets.ai_service.query_bedrock")
    def test_fetch_open_tickets_with_same_department(self, mock_query_bedrock):
        # Ensure AI processing data exists for the current ticket
        ai_process_ticket(self.ticket)

        # Fetch open tickets in the same department (excluding the current ticket)
        ai_assigned_department = self.ticket.ai_processing.ai_assigned_department

        potential_tickets = Ticket.objects.filter(
            status="in_progress",
            ai_processing__ai_assigned_department=ai_assigned_department,
        ).exclude(id=self.ticket.id)

        # Verify that the second ticket is fetched (same department)
        self.assertIn(self.ticket_2, potential_tickets)
        # Verify that the third ticket is NOT fetched (different department)
        self.assertNotIn(self.ticket_3, potential_tickets)
        # Ensure only one ticket is excluded (the current ticket)
        self.assertEqual(len(potential_tickets), 1)

    @patch("tickets.ai_service.query_bedrock")
    def test_classify_department(self, mock_query_bedrock):
        mock_query_bedrock.return_value = "Admissions"
        department = classify_department(self.ticket.description)
        self.assertEqual(department, "Admissions")
        mock_query_bedrock.assert_called_once_with(self.ticket.description)

    @patch("tickets.ai_service.query_bedrock")
    def test_predict_priority(self, mock_query_bedrock):
        mock_query_bedrock.return_value = "High"
        priority = predict_priority(self.ticket.description)
        self.assertEqual(priority, "High")
        mock_query_bedrock.assert_called_once_with(self.ticket.description)

    @patch("tickets.ai_service.query_bedrock")
    def test_generate_ai_answer(self, mock_query_bedrock):
        mock_query_bedrock.return_value = "You can register for courses via the student portal."
        ai_answer = generate_ai_answer(self.ticket.description)
        self.assertEqual(ai_answer, "You can register for courses via the student portal.")
        mock_query_bedrock.assert_called_once_with(self.ticket.description)

    @patch("tickets.ai_service.query_bedrock")
    def test_ai_process_ticket(self, mock_query_bedrock):
        mock_query_bedrock.side_effect = [
            "Admissions", 
            "You can register for courses via the student portal.", 
            "High"
        ]

        ai_process_ticket(self.ticket)

        # Verify that AITicketProcessing was created
        ai_processing = AITicketProcessing.objects.get(ticket=self.ticket)
        self.assertEqual(ai_processing.ai_assigned_department, "Admissions")
        self.assertEqual(ai_processing.ai_generated_response, "You can register for courses via the student portal.")
        self.assertEqual(ai_processing.ai_assigned_priority, "High")

        # Verify that the ticket's priority was updated
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.priority, "High")

    @patch("tickets.ai_service.query_bedrock")
    def test_find_potential_tickets_to_merge(self, mock_query_bedrock):
        # Create additional tickets
        ticket_2 = Ticket.objects.create(
            title="Course Registration Issue",
            description="I am unable to register for my courses.",
            status="in_progress",
        )
        ticket_3 = Ticket.objects.create(
            title="Unrelated Issue",
            description="I need help with my dormitory allocation.",
            status="in_progress",
        )

        # Mock responses for similarity checks
        mock_query_bedrock.side_effect = ["yes", "no"]

        similar_tickets = find_potential_tickets_to_merge(self.ticket)

        # Verify that only the similar ticket is returned
        self.assertEqual(len(similar_tickets), 1)
        self.assertEqual(similar_tickets[0], ticket_2)

        # Verify that a MergedTicket entry was created
        merged_ticket = MergedTicket.objects.get(primary_ticket=self.ticket)
        self.assertIn(ticket_2, merged_ticket.suggested_merged_tickets.all())
        self.assertNotIn(ticket_3, merged_ticket.suggested_merged_tickets.all())

        mock_query_bedrock.assert_called()

    @patch("tickets.ai_service.query_bedrock")
    def test_query_bedrock_failure(self, mock_query_bedrock):
        """Test that a ClientError is handled gracefully."""
        mock_query_bedrock.side_effect = ClientError(
            error_response={"Error": {"Code": "500", "Message": "Internal Server Error"}},
            operation_name="InvokeModel",
        )
        result = query_bedrock("Test input")
        self.assertEqual(result, "")  # Ensure an empty string is returned
        mock_query_bedrock.assert_called_once_with("Test input")

    @patch("tickets.ai_service.query_bedrock")
    def test_query_bedrock_success(self, mock_query_bedrock):
        """Test that query_bedrock returns the expected result."""
        mock_query_bedrock.return_value = "Success"
        result = query_bedrock("Test input")
        self.assertEqual(result, "Success")
        mock_query_bedrock.assert_called_once_with("Test input")



class TicketMergingTests(TestCase):

    def setUp(self):
        # Create tickets for testing
        self.ticket = Ticket.objects.create(
            title="Test Ticket 1",
            description="Issue with course registration.",
            status="in_progress",
        )
        self.ticket_2 = Ticket.objects.create(
            title="Test Ticket 2",
            description="Similar issue with course registration.",
            status="in_progress",
        )
        self.ticket_3 = Ticket.objects.create(
            title="Test Ticket 3",
            description="Unrelated issue with IT support.",
            status="in_progress",
        )

        # Create AI processing data for these tickets
        ai_process_ticket(self.ticket)
        ai_process_ticket(self.ticket_2)
        ai_process_ticket(self.ticket_3)

    @patch("tickets.ai_service.query_bedrock")
    def test_compare_and_merge_tickets(self, mock_query_bedrock):
        # Mock the response of query_bedrock to simulate the comparison
        mock_query_bedrock.side_effect = lambda prompt: "Yes" if "course registration" in prompt else "No"

        # Fetch open tickets in the same department and exclude the current ticket
        ai_assigned_department = self.ticket.ai_processing.ai_assigned_department
        potential_tickets = Ticket.objects.filter(
            status="in_progress",
            ai_processing__ai_assigned_department=ai_assigned_department,
        ).exclude(id=self.ticket.id)

        similar_tickets = []

        # Compare tickets
        for potential_ticket in potential_tickets:
            # Generate the prompt for comparison
            prompt = f"""
            Determine whether the following tickets should be merged. Consider their similarity.
            The current ticket: '{self.ticket.title}' - {self.ticket.description}
            The potential ticket: '{potential_ticket.title}' - {potential_ticket.description}
            Should these tickets be merged? Return "Yes" or "No".
            """
            print(f"Checking ticket {potential_ticket.id}...")  # Debug print

            result = mock_query_bedrock(prompt)

            if result.lower() == "yes":
                similar_tickets.append(potential_ticket)

        # Test if the correct tickets are identified for merging
        self.assertIn(self.ticket_2, similar_tickets)  # The second ticket should be considered similar
        self.assertNotIn(self.ticket_3, similar_tickets)  # The third ticket should not be considered similar

        # Check if a merged ticket entry is created for the primary ticket
        if similar_tickets:
            merged_ticket = MergedTicket.objects.get(primary_ticket=self.ticket)
            self.assertEqual(merged_ticket.primary_ticket, self.ticket)
            self.assertEqual(set(merged_ticket.suggested_merged_tickets.all()), {self.ticket_2})

        # Check that no unnecessary merged tickets are created for non-similar tickets
        merged_ticket_non_similar = MergedTicket.objects.filter(primary_ticket=self.ticket_3)
        self.assertFalse(merged_ticket_non_similar.exists())

    @patch("tickets.ai_service.query_bedrock")
    def test_no_merge_for_dissimilar_tickets(self, mock_query_bedrock):
        # Mocking the query_bedrock to return 'No' for dissimilar tickets
        mock_query_bedrock.return_value = "No"

        # Test when no tickets are similar
        ai_assigned_department = self.ticket.ai_processing.ai_assigned_department
        potential_tickets = Ticket.objects.filter(
            status="in_progress",
            ai_processing__ai_assigned_department=ai_assigned_department,
        ).exclude(id=self.ticket.id)

        similar_tickets = []

        # Compare tickets
        for potential_ticket in potential_tickets:
            prompt = f"""
            Determine whether the following tickets should be merged. Consider their similarity.
            The current ticket: '{self.ticket.title}' - {self.ticket.description}
            The potential ticket: '{potential_ticket.title}' - {potential_ticket.description}
            Should these tickets be merged? Return "Yes" or "No".
            """
            result = mock_query_bedrock(prompt)

            if result.lower() == "yes":
                similar_tickets.append(potential_ticket)

        # Test that no tickets are added to the similar_tickets list
        self.assertEqual(len(similar_tickets), 0)

        # No MergedTicket should be created when no tickets are similar
        merged_ticket = MergedTicket.objects.filter(primary_ticket=self.ticket)
        self.assertFalse(merged_ticket.exists())
