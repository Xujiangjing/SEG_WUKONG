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
from django.views.decorators.http import require_POST
from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView, UpdateView
from tickets.forms import (
    LogInForm,
    PasswordForm,
    ReturnTicketForm,
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


from tickets.ai_service import ai_process_ticket, find_potential_tickets_to_merge

from tickets.models import Ticket, TicketActivity, Department, MergedTicket


from tickets.forms import UserForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Display user profile editing screen, and handle profile modifications."""

    model = UserForm  # The model to update
    template_name = "profile.html"  # Template to use
    form_class = UserForm  # The form to render and validate

    def get_object(self):
        """Return the object (user) to be updated."""
        user = self.request.user
        return user

    def get_success_url(self):
        """Return redirect URL after successful update."""
        messages.add_message(self.request, messages.SUCCESS, "Profile updated!")
        return reverse(settings.REDIRECT_URL_WHEN_LOGGED_IN)


@login_required
def get_user_role(request):
    """Return the role of the current user."""
    role = "unknown"
    if request.user.is_program_officer:
        role = "program_officer"
    elif request.user.is_specialist:
        role = "specialist"
    elif request.user.is_student:
        role = "student"
    return JsonResponse({"role": role})
