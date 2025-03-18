from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView, UpdateView
from tickets.forms import (
    LogInForm,
    PasswordForm,
    ReturnTicketForm,
    SignUpForm,
    SupplementTicketForm,
    TicketAttachmentForm,
    TicketForm,
    UserForm,
)
from tickets.helpers import login_prohibited
from tickets.models import (
    AITicketProcessing,
    Ticket,
    TicketActivity,
    TicketAttachment,
    User,
)

from tickets.helpers import (
    handle_uploaded_file_in_chunks,
    send_ticket_confirmation_email,
)

from tickets.ai_service import ai_process_ticket, find_potential_tickets_to_merge

from tickets.models import Ticket, TicketActivity, Department, MergedTicket


@login_prohibited
def home(request):
    """Display the application's start/home screen."""

    return render(request, "home.html")


class TicketListView(ListView):
    model = Ticket
    template_name = "tickets/ticket_list.html"
    context_object_name = "tickets"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_student():
            messages.error(
                request, "You do not have permission to view the ticket list."
            )
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if self.request.user.is_program_officer():
            return Ticket.objects.all()
        elif self.request.user.is_specialist():
            return Ticket.objects.filter(assigned_user=self.request.user)
        elif self.request.user.is_student():
            return Ticket.objects.filter(creator=self.request.user)


class CreateTicketView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = "tickets/create_ticket.html"
    success_url = "/tickets/"

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_authenticated and not request.user.is_student():
            messages.error(request, "Only students can create tickets.")
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):

        ticket = form.save(commit=False)
        ticket.creator = self.request.user
        ticket.status = "in_progress"

        if self.request.user.is_student():
            ticket.priority = "low"

        ticket.save()

        existing_ticket = (
            Ticket.objects.filter(title=ticket.title, status="in_progress")
            .exclude(id=ticket.id)
            .first()
        )

        if existing_ticket:

            existing_ticket.description += (
                f"\n\nMerged with ticket ID: {ticket.id}. "
                f"New description: {ticket.description}"
            )
            existing_ticket.save()

            files = self.request.FILES.getlist("file")
            for f in files:
                handle_uploaded_file_in_chunks(existing_ticket, f)

            TicketActivity.objects.create(
                ticket=existing_ticket,
                action="merged",
                action_by=self.request.user,
                comment=f"Merged with ticket {ticket.id}",
            )

            ticket.delete()

            messages.success(
                self.request,
                f"Ticket merged with existing ticket {existing_ticket.id} successfully!",
            )
            return redirect("ticket_detail", ticket_id=existing_ticket.id)

        else:
            files = self.request.FILES.getlist("file")
            for f in files:
                handle_uploaded_file_in_chunks(ticket, f)

            TicketActivity.objects.create(
                ticket=ticket, action="created", action_by=self.request.user
            )

            ai_process_ticket(ticket)

            send_ticket_confirmation_email(ticket)
            messages.success(self.request, "Query submitted successfully!")
            return redirect("ticket_detail", ticket_id=ticket.id)


@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    attachments = ticket.attachments.order_by("uploaded_at")

    activities = TicketActivity.objects.filter(ticket=ticket).order_by("-action_time")
    formatted_activities = [
        {
            "username": activity.action_by.username,
            "action": activity.get_action_display(),
            "action_time": date_format(activity.action_time, "F j, Y, g:i a"),
            "comment": activity.comment or "No comments.",
        }
        for activity in activities
    ]

    if (
        not request.user.is_student()
        and ticket.status == "in_progress"
        and ticket.return_reason
    ):
        messages.warning(request, "This ticket is waiting for the student to update.")

    if (
        request.user != ticket.creator
        and request.user != ticket.assigned_user
        and not request.user.is_program_officer()
    ):
        return redirect("dashboard")

    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "activities": formatted_activities,
            "attachments": attachments,
        },
    )
