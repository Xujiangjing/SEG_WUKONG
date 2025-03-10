from django.conf import settings
from django.shortcuts import redirect
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail



def login_prohibited(view_function):
    """Decorator for view functions that redirect users away if they are logged in."""
    
    def modified_view_function(request):
        if request.user.is_authenticated:
            return redirect(settings.REDIRECT_URL_WHEN_LOGGED_IN)
        else:
            return view_function(request)
    return modified_view_function

# Student will receive an email when they submit a ticket in tickets system
def send_ticket_confirmation_email(ticket):
    subject = f"Ticket #{ticket.id} Confirmation"
    recipient_email = ticket.creator.email
    context = {
        'user': ticket.creator,
        'ticket': ticket
    }

    html_content = render_to_string("emails/ticket_confirmation.html", context)
    text_content = strip_tags(html_content)  # Convert HTML to plain text

    email = EmailMultiAlternatives(subject, text_content, "wukonghelpdesk@gmail", [recipient_email])
    email.attach_alternative(html_content, "text/html")
    email.send()

# This function sends an email to the student when their ticket has been responded to.
def send_response_notification_email(student_email, ticket_title, response_message, ticket_id):
    """Sends an email to notify the student that their ticket has been responded to."""
    
    subject = f"Update on Your Ticket: '{ticket_title}'"
    
    context = {
        'student_name' :student_email.split('@')[0],
        'ticket_title': ticket_title,
        'response_message': response_message,
        'ticket_id': ticket_id, 
    }
    
    html_message = render_to_string("emails/response_notification.html", context)
    text_message = strip_tags(html_message)  
    
    send_mail(
        subject,
        text_message,  # Plain text version
        settings.EMAIL_HOST_USER,
        [student_email],
        fail_silently=False,
        html_message=html_message  # HTML version
    )
