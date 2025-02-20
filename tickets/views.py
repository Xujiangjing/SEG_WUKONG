from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Count, Q
from django.shortcuts import redirect, render,get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView, UpdateView
from tickets.forms import (LogInForm, PasswordForm, SignUpForm,
                           TicketAttachmentForm, TicketForm, UserForm,
                           ReturnTicketForm, SupplementTicketForm)
from tickets.helpers import login_prohibited
from tickets.models import Ticket, TicketActivity, TicketAttachment, User


@login_required
def dashboard(request):
    current_user = request.user
    search_query = request.GET.get('search', '')
    
    if current_user.is_program_officer() or current_user.is_specialist():
        if request.method == "POST" and "respond_ticket" in request.POST:
            ticket_id = request.POST.get("ticket_id")
            response_message = request.POST.get("response_message")
            ticket = Ticket.objects.get(id=ticket_id)
            if ticket.answers!=None:
                ticket.answers += "\n" 
            else :
                ticket.answers = ""
            ticket.answers += f"Response by {current_user.username}: {response_message}"
            ticket.save()  

            ticket_activity = TicketActivity.objects.create(
                ticket=ticket,
                action='responded',
                action_by=current_user,
                comment=response_message
            )
            ticket_activity.save()
            return redirect('dashboard') 
    if current_user.is_program_officer():
        if search_query:
            all_tickets = Ticket.objects.filter(title__icontains=search_query)
        else:
            all_tickets = Ticket.objects.all()

        ticket_stats = User.objects.filter(role='specialists').annotate(ticket_count=Count('assigned_tickets'))

        if request.method == 'POST' and 'redirect_ticket' in request.POST:
            ticket_id = request.POST.get('ticket_id')
            new_assignee_id = request.POST.get('new_assignee_id')
            ticket = Ticket.objects.get(id=ticket_id)
            new_assignee = User.objects.get(id=new_assignee_id)
            ticket.assigned_user = new_assignee
            ticket.latest_action = 'redirected'
            ticket.save()

            ticket_activity = TicketActivity.objects.create(
                ticket=ticket,
                action='redirected',
                action_by=current_user,
                comment=f"Redirected to {new_assignee.username}"
            )
            ticket_activity.save()
            return redirect('dashboard') 
            
        return render(request, 'dashboard.html', {
            'user': current_user,
            'all_tickets': all_tickets,
            'ticket_stats': ticket_stats,
        })
    
    elif current_user.is_student():
        student_tickets = Ticket.objects.filter(creator=current_user)
        if search_query:
            student_tickets = student_tickets.filter(title__icontains=search_query)
        
        return render(request, 'dashboard.html', {
            'user': current_user,
            'student_tickets': student_tickets,
        })
    
    elif current_user.is_specialist():
        assigned_tickets = Ticket.objects.filter(assigned_user=current_user)
        if search_query:
            assigned_tickets = assigned_tickets.filter(title__icontains=search_query)
        
        return render(request, 'dashboard.html', {
            'user': current_user,
            'assigned_tickets': assigned_tickets,
        })

    return render(request, 'dashboard.html', {'user': current_user, 'message': "You do not have permission to view this dashboard."})


@login_prohibited
def home(request):
    """Display the application's start/home screen."""

    return render(request, 'home.html')


class LoginProhibitedMixin:
    """Mixin that redirects when a user is logged in."""

    redirect_when_logged_in_url = None

    def dispatch(self, *args, **kwargs):
        """Redirect when logged in, or dispatch as normal otherwise."""
        if self.request.user.is_authenticated:
            return self.handle_already_logged_in(*args, **kwargs)
        return super().dispatch(*args, **kwargs)

    def handle_already_logged_in(self, *args, **kwargs):
        url = self.get_redirect_when_logged_in_url()
        return redirect(url)

    def get_redirect_when_logged_in_url(self):
        """Returns the url to redirect to when not logged in."""
        if self.redirect_when_logged_in_url is None:
            raise ImproperlyConfigured(
                "LoginProhibitedMixin requires either a value for "
                "'redirect_when_logged_in_url', or an implementation for "
                "'get_redirect_when_logged_in_url()'."
            )
        else:
            return self.redirect_when_logged_in_url


class LogInView(LoginProhibitedMixin, View):
    """Display login screen and handle user login."""

    http_method_names = ['get', 'post']
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN

    def get(self, request):
        """Display log in template."""

        self.next = request.GET.get('next') or ''
        return self.render()

    def post(self, request):
        """Handle log in attempt."""

        form = LogInForm(request.POST)
        self.next = request.POST.get('next') or settings.REDIRECT_URL_WHEN_LOGGED_IN
        user = form.get_user()
        if user is not None:
            login(request, user)
            return redirect(self.next)
        messages.add_message(request, messages.ERROR, "The credentials provided were invalid!")
        return self.render()

    def render(self):
        """Render log in template with blank log in form."""

        form = LogInForm()
        return render(self.request, 'log_in.html', {'form': form, 'next': self.next})


def log_out(request):
    """Log out the current user"""

    logout(request)
    return redirect('home')


class PasswordView(LoginRequiredMixin, FormView):
    """Display password change screen and handle password change requests."""

    template_name = 'password.html'
    form_class = PasswordForm

    def get_form_kwargs(self, **kwargs):
        """Pass the current user to the password change form."""

        kwargs = super().get_form_kwargs(**kwargs)
        kwargs.update({'user': self.request.user})
        return kwargs

    def form_valid(self, form):
        """Handle valid form by saving the new password."""

        form.save()
        login(self.request, self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect the user after successful password change."""

        messages.add_message(self.request, messages.SUCCESS, "Password updated!")
        return reverse('dashboard')


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Display user profile editing screen, and handle profile modifications."""

    model = UserForm
    template_name = "profile.html"
    form_class = UserForm

    def get_object(self):
        """Return the object (user) to be updated."""
        user = self.request.user
        return user

    def get_success_url(self):
        """Return redirect URL after successful update."""
        messages.add_message(self.request, messages.SUCCESS, "Profile updated!")
        return reverse(settings.REDIRECT_URL_WHEN_LOGGED_IN)


class SignUpView(LoginProhibitedMixin, FormView):
    form_class = SignUpForm
    template_name = "sign_up.html"
    redirect_when_logged_in_url = settings.REDIRECT_URL_WHEN_LOGGED_IN

    def form_valid(self, form):
        self.object = form.save()
        login(self.request, self.object)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(settings.REDIRECT_URL_WHEN_LOGGED_IN)

class TicketListView(ListView):
    model = Ticket
    template_name = 'tickets/ticket_list.html'  
    context_object_name = 'tickets'

## This is the view for the ticket creation page
class CreateTicketView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = 'tickets/create_ticket.html'
    success_url = '/tickets/'

    def form_valid(self, form):
        ticket = form.save(commit=False)
        ticket.creator = self.request.user
        ticket.status = 'open'
        ticket.save()
        
        ## Upload multiple files
        files = self.request.FILES.getlist('file')
        for file in files:
            TicketAttachment.objects.create(ticket=ticket, file=file)
        
        TicketActivity.objects.create(
            ticket=ticket,
            action='created',
            action_by=self.request.user
        )
        
        # Here is your success message + redirect
        messages.success(self.request, 'Query submitted successfully!')
        return redirect('ticket_detail', pk=ticket.pk)


## This is the view for the ticket detail page
class TicketDetailView(DetailView):
    model = Ticket
    template_name = 'tickets/ticket_detail.html'
    context_object_name = 'ticket'


@login_required
def close_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.user.is_student() and request.user == ticket.creator:
        ticket.status = 'closed'
        ticket.save()
        messages.success(request, 'Ticket closed successfully.')
    else:
        messages.error(request, 'You do not have permission to close this ticket.')
    return redirect('dashboard')

@login_required
def return_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_program_officer() or ticket.status != 'open':
        return redirect('ticket_list')

    if request.method == 'POST':
        form = ReturnTicketForm(request.POST)
        if form.is_valid():
            ticket.status = 'returned'
            ticket.return_reason = form.cleaned_data['return_reason']
            ticket.save()
            return redirect('ticket_list')
    else:
        form = ReturnTicketForm()

    return render(request, 'tickets/return_ticket.html', {'form': form, 'ticket': ticket})


@login_required
def supplement_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_student() or ticket.status != 'returned':
        return redirect('ticket_list')

    if request.user != ticket.creator:
        messages.error(request, "You do not have permission to modify this ticket.")
        return redirect("ticket_list")

    if request.method == 'POST':
        form = SupplementTicketForm(request.POST)
        if form.is_valid():
            ticket.description += "\n\nSupplement: " + form.cleaned_data['supplement_info']
            ticket.status = 'open'
            ticket.save()
            return redirect('ticket_list')
    else:
        form = SupplementTicketForm()

    return render(request, 'tickets/supplement_ticket.html', {'form': form, 'ticket': ticket})