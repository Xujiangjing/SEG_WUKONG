# tickets/tests/views/test_dashboard_filter.py

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models import Ticket, Department
from django.utils import timezone
import datetime
from uuid import uuid4
from django.db.models import Q

User = get_user_model()


class DashboardFilterViewTestCase(TestCase):
    """
    Tests for filtering, sorting, and searching functionality
    on the dashboard view.
    """

    fixtures = ['tickets/tests/fixtures/default_user.json']

    def setUp(self):
        """
        Create several users (with different roles) and various tickets
        having different statuses, priorities, and creation times.
        """

        # Create departments
        self.dept_general = Department.objects.create(name='general_enquiry')
        self.dept_it = Department.objects.create(name='it_support')

        # Use UUID suffix to ensure unique username/email for each test run
        suffix_prog = str(uuid4())[:8]
        suffix_spec = str(uuid4())[:8]
        suffix_stud = str(uuid4())[:8]

        # Create Program Officer
        self.program_officer = User.objects.create_user(
            username=f'@programofficer_{suffix_prog}',
            email=f'program_{suffix_prog}@example.org',
            password='Password123',
            role='program_officers',
            department=self.dept_general
        )

        # Create Specialist
        self.specialist = User.objects.create_user(
            username=f'@specialist_{suffix_spec}',
            email=f'spec_{suffix_spec}@example.org',
            password='Password123',
            role='specialists',
            department=self.dept_it
        )

        # Create Student
        self.student = User.objects.create_user(
            username=f'@student_{suffix_stud}',
            email=f'student_{suffix_stud}@example.org',
            password='Password123',
            role='students'
        )

        # Create tickets with various statuses, priorities, etc.
        now = timezone.now()

        # ticket_open: 2 days ago
        self.ticket_open = Ticket.objects.create(
            creator=self.student,
            title="Open Ticket",
            description="Need help with something",
            status="open",
            priority="medium",
            assigned_department=self.dept_general.name,
            created_at=now  # will fix below
        )

        # ticket_closed: 3 days ago
        self.ticket_closed = Ticket.objects.create(
            creator=self.student,
            title="Closed Ticket",
            description="Issue resolved",
            status="closed",
            priority="low",
            assigned_department=self.dept_it.name,
            created_at=now  # will fix below
        )

        # ticket_in_progress: 1 day ago
        self.ticket_in_progress = Ticket.objects.create(
            creator=self.student,
            title="InProgress Ticket",
            description="Ongoing issue",
            status="in_progress",
            priority="high",
            assigned_department=self.dept_it.name,
            created_at=now  # will fix below
        )

        # Manually adjust created_at to ensure distinct ordering
        # ticket_in_progress  => 1 day ago
        self.ticket_in_progress.created_at = now - datetime.timedelta(days=1, seconds=1)
        self.ticket_in_progress.save()

        # ticket_open         => 2 days ago
        self.ticket_open.created_at = now - datetime.timedelta(days=2, seconds=1)
        self.ticket_open.save()

        # ticket_closed       => 3 days ago
        self.ticket_closed.created_at = now - datetime.timedelta(days=3, seconds=1)
        self.ticket_closed.save()

        # Dashboard URL
        self.url = reverse('dashboard')

    def test_redirect_when_not_logged_in(self):
        """
        Accessing the dashboard without logging in should redirect
        to the log_in page.
        """
        response = self.client.get(self.url)
        login_url = reverse('log_in')
        expected_redirect = f"{login_url}?next={self.url}"
        self.assertRedirects(response, expected_redirect)

    def test_filter_by_status_open(self):
        """
        As a program officer, filter tickets by status 'open'
        and ensure only open tickets show up.
        """
        self.client.login(username=self.program_officer.username, password='Password123')
        response = self.client.get(self.url + '?status=open')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')

        all_tickets = response.context.get('all_tickets', [])
        self.assertIsNotNone(all_tickets)

        # Should only contain the ticket with status="open"
        statuses = [t.status for t in all_tickets]
        self.assertIn('open', statuses)
        self.assertNotIn('closed', statuses)
        self.assertNotIn('in_progress', statuses)

    def test_filter_by_status_closed(self):
        """
        Filter by 'closed' status. Only closed tickets should appear.
        """
        self.client.login(username=self.program_officer.username, password='Password123')
        response = self.client.get(self.url + '?status=closed')
        self.assertEqual(response.status_code, 200)
        all_tickets = response.context.get('all_tickets', [])
        self.assertEqual(len(all_tickets), 1)
        self.assertEqual(all_tickets[0].title, 'Closed Ticket')

    def test_sort_by_date_desc(self):
        """
        Sorting by date descending. The newest ticket should appear first.
        (We assume ?sort=date_desc for descending creation time.)
        """
        self.client.login(username=self.program_officer.username, password='Password123')
        response = self.client.get(self.url + '?sort=date_desc')
        self.assertEqual(response.status_code, 200)
        all_tickets = response.context.get('all_tickets', [])

        # all_tickets should follow [in_progress (1 day ago), open (2 days ago), closed (3 days ago)]
        # so we check: all_tickets[0].created_at > all_tickets[1].created_at > all_tickets[2].created_at
        self.assertGreater(all_tickets[0].created_at, all_tickets[1].created_at)
        self.assertGreater(all_tickets[1].created_at, all_tickets[2].created_at)

    def test_sort_by_priority_asc(self):
        """
        Sorting by priority ascending. (We assume priorities: low < medium < high < urgent).
        e.g. If ?sort=priority_asc, we expect 'low', 'medium', 'high' in that order.
        """
        self.client.login(username=self.program_officer.username, password='Password123')
        response = self.client.get(self.url + '?sort=priority_asc')
        self.assertEqual(response.status_code, 200)
        all_tickets = response.context.get('all_tickets', [])

        # We expect closed ticket (low) first, then open (medium), then in_progress (high)
        priorities = [ticket.priority for ticket in all_tickets]
        self.assertEqual(priorities, ['low', 'medium', 'high'])

    def test_search_functionality(self):
        """
        Searching 'Ongoing' should find the 'InProgress Ticket',
        ignoring others. We assume 'search' param is used against title/description.
        """
        self.client.login(username=self.program_officer.username, password='Password123')
        response = self.client.get(self.url + '?search=Ongoing')
        self.assertEqual(response.status_code, 200)
        all_tickets = response.context.get('all_tickets', [])

        # only the "InProgress Ticket" has "Ongoing" in description
        self.assertEqual(len(all_tickets), 1)
        self.assertEqual(all_tickets[0].title, "InProgress Ticket")

    def test_combined_filter_search(self):
        """
        Searching 'Issue' + status='in_progress'
        should yield only in-progress tickets containing 'Issue' in the description.
        """
        self.client.login(username=self.program_officer.username, password='Password123')
        response = self.client.get(self.url + '?status=in_progress&search=Issue')
        self.assertEqual(response.status_code, 200)
        all_tickets = response.context.get('all_tickets', [])

        # ticket_in_progress has "Ongoing issue" in the description
        # ticket_open => "Need help with something"
        # ticket_closed => "Issue resolved" but status=closed
        self.assertEqual(len(all_tickets), 1)
        self.assertEqual(all_tickets[0].title, "InProgress Ticket")
