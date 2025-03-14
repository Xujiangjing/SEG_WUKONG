"""
URL configuration for query_hub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from tickets.views import *
from tickets.views.base_views import get_user_role
from tickets.views import (
    authentication,
    user_management,
    ticket_operations,
    dashboard,
    base_views,
)
from tickets.views.dashboard import (
    dashboard_redirect,
    program_officer_dashboard,
    student_dashboard,
    specialist_dashboard,
)
from tickets.views.ticket_operations import (
    close_ticket,
    return_ticket,
    supplement_ticket,
    merge_ticket,
    respond_ticket,
    update_ticket,
    manage_ticket_page,
    submit_ticket,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", base_views.home, name="home"),
    path("log_in/", authentication.LogInView.as_view(), name="log_in"),
    path("log_out/", authentication.log_out, name="log_out"),
    path("password/", authentication.PasswordView.as_view(), name="password"),
    path("profile/", user_management.ProfileUpdateView.as_view(), name="profile"),
    path("tickets/", base_views.TicketListView.as_view(), name="ticket_list"),
    path(
        "tickets/<uuid:pk>/",
        base_views.TicketDetailView.as_view(),
        name="ticket_detail",
    ),
    path(
        "close_ticket/<uuid:ticket_id>/",
        ticket_operations.close_ticket,
        name="close_ticket",
    ),
    path(
        "ticket/<uuid:pk>/return/",
        ticket_operations.return_ticket,
        name="return_ticket",
    ),
    path(
        "ticket/<uuid:pk>/supplement/",
        ticket_operations.supplement_ticket,
        name="supplement_ticket",
    ),
    path(
        "ticket/<uuid:ticket_id>/detail/",
        base_views.ticket_detail,
        name="ticket_detail",
    ),
    path("ticket/submit/", ticket_operations.submit_ticket, name="submit_ticket"),
    path(
        "tickets/create/", base_views.CreateTicketView.as_view(), name="create_ticket"
    ),
    path("dashboard/", dashboard_redirect, name="dashboard"),
    path(
        "dashboard/dashboard_program_officer/",
        dashboard.program_officer_dashboard,
        name="dashboard_program_officer",
    ),
    path(
        "dashboard/dashboard_student/",
        dashboard.student_dashboard,
        name="dashboard_student",
    ),
    path(
        "dashboard/dashboard_specialist/",
        dashboard.specialist_dashboard,
        name="dashboard_specialist",
    ),
    path(
        "tickets/manage_ticket_page/<uuid:ticket_id>/",
        ticket_operations.manage_ticket_page,
        name="manage_ticket_page",
    ),
    path("get_user_role/", get_user_role, name="get_user_role"),
    path(
        "tickets/views/respond/<int:ticket_id>/", respond_ticket, name="respond_ticket"
    ),
    path("tickets/views/return/<int:ticket_id>/", return_ticket, name="return_ticket"),
]
urlpatterns += static(
    settings.STATIC_URL, document_root=settings.STATIC_ROOT
)  # pragma: no cover
