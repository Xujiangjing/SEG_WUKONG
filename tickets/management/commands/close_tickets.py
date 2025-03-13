from django.core.management.base import BaseCommand
from django.utils import timezone
from tickets.models import Ticket,DailyTicketClosureReport
from datetime import timedelta

class Command(BaseCommand):
    help = 'Close tickets that have not been updated in the last 7 days'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        today = now.date()
        stale_tickets = Ticket.objects.filter(
            status__in=['open', 'in_progress', 'resolved'],
            updated_at__lt=now - timedelta(days=7)
        )
        closed_by_inactivity_count = stale_tickets.count()
        stale_tickets.update(status='closed', latest_action='closed_by_inactivity')

        # Update or create DailyTicketClosureReport for each department
        for ticket in stale_tickets:
            report, created = DailyTicketClosureReport.objects.get_or_create(
                date=today,
                department=ticket.assigned_department,
                defaults={'closed_by_inactivity': 0, 'closed_manually': 0}
            )
            report.closed_by_inactivity += 1
            report.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully closed {closed_by_inactivity_count} stale tickets by inactivity'))

        urgent_tickets = Ticket.objects.filter(
            status__in=['open', 'in_progress', 'resolved'],
            updated_at__lt=now - timedelta(days=6)
        )
        ucount = urgent_tickets.update(priority='urgent')
        self.stdout.write(self.style.SUCCESS(f'Successfully closed {ucount} stale tickets'))