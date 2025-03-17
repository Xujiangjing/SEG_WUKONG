from .dashboard import (
    dashboard_redirect,
    program_officer_dashboard,
    student_dashboard,
    specialist_dashboard,
)
from .ticket_operations import (
    close_ticket,
    return_ticket,
    supplement_ticket,
    merge_ticket,
    respond_ticket,
    update_ticket,
    manage_ticket_page,
)
from .authentication import LoginProhibitedMixin, LogInView, log_out, PasswordView
from .user_management import ProfileUpdateView
from .base_views import (
    home,
    TicketListView,
    ticket_detail,
    CreateTicketView,
)
from .user_management import get_user_role
