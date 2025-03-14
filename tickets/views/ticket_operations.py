from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.formats import date_format
from django.views.decorators.http import require_POST
from tickets.forms import ReturnTicketForm, SupplementTicketForm, TicketForm
from tickets.ai_service import ai_process_ticket, find_potential_tickets_to_merge
from tickets.helpers import send_ticket_confirmation_email
from tickets.models import (
    TicketAttachment,
    User,
    Ticket,
    TicketActivity,
    Department,
    MergedTicket,
)


@login_required
def close_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.user.is_student() and request.user == ticket.creator:
        ticket.status = "closed"
        ticket.save()
        messages.success(request, "Ticket closed successfully.")
    else:
        messages.error(request, "You do not have permission to close this ticket.")
    return redirect("dashboard")


@login_required
def return_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not request.user.is_program_officer() or ticket.status != "open":
        return redirect("ticket_list")

    if request.method == "POST":
        form = ReturnTicketForm(request.POST)
        if form.is_valid():
            ticket.status = "returned"
            ticket.return_reason = form.cleaned_data["return_reason"]
            ticket.save()
            return redirect("ticket_list")
    else:
        form = ReturnTicketForm()

    return render(
        request, "tickets/return_ticket.html", {"form": form, "ticket": ticket}
    )


@login_required
def supplement_ticket(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.user != ticket.creator or ticket.status != "returned":
        return redirect("ticket_list")

    if request.method == "POST":
        form = SupplementTicketForm(request.POST)
        if form.is_valid():
            ticket.description += (
                f"\n\nSupplement: {form.cleaned_data['supplement_info']}"
            )
            ticket.status = "open"
            ticket.save()
            return redirect("ticket_list")
    else:
        form = SupplementTicketForm()

    return render(
        request, "tickets/supplement_ticket.html", {"form": form, "ticket": ticket}
    )


@login_required
@require_POST
def merge_ticket(request, ticket_id, potential_ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    potential_ticket = get_object_or_404(Ticket, id=potential_ticket_id)
    merged_ticket, created = MergedTicket.objects.get_or_create(primary_ticket=ticket)

    if potential_ticket in merged_ticket.approved_merged_tickets.all():
        merged_ticket.approved_merged_tickets.remove(potential_ticket)
        action = "unmerged"
    else:
        merged_ticket.approved_merged_tickets.add(potential_ticket)
        action = "merged"

    merged_ticket.save()
    return redirect("respond_ticket_page", ticket_id=ticket.id)


@login_required
def respond_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.user != ticket.assigned_user and not request.user.is_program_officer():
        return redirect("dashboard")

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

    if request.method == "POST" and "response_message" in request.POST:
        response_message = request.POST.get("response_message")
        ticket.answers = (
            ticket.answers or ""
        ) + f"\nResponse by {request.user.username}: {response_message}"
        ticket.status = "in_progress"
        ticket.save()
        TicketActivity.objects.create(
            ticket=ticket,
            action="responded",
            action_by=request.user,
            comment=response_message,
        )
        messages.success(request, "Response sent successfully.")
        return redirect("ticket_detail", ticket_id=ticket.id)

    return render(
        request,
        "ticket_detail.html",
        {"ticket": ticket, "activities": formatted_activities},
    )


@login_required
def update_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.user != ticket.creator:
        messages.error(request, "You do not have permission to modify this ticket.")
        return redirect("dashboard")

    if request.method == "POST" and "update_message" in request.POST:
        update_message = request.POST.get("update_message")
        ticket.description += (
            f"\n\nSupplement: {request.user.username}: {update_message}"
        )
        ticket.status = "open"
        ticket.latest_action = "status_updated"
        ticket.save()
        TicketActivity.objects.create(
            ticket=ticket,
            action="status_updated",
            action_by=request.user,
            comment=update_message,
        )

    return redirect("dashboard")


@login_required
def manage_ticket_page(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related("creator", "assigned_user"), id=ticket_id
    )

    user = request.user
    is_student = user.is_student()
    is_specialist = user.is_specialist()
    is_program_officer = user.is_program_officer()

    actions = []
    if is_student:
        actions.extend(["update_ticket", "close_ticket"])

        return render(
            request,
            "tickets/manage_tickets_page_for_student.html",
            {"ticket": ticket, "actions": actions},
        )

    if is_specialist:
        actions.extend(["respond_ticket", "return_ticket"])

        return render(
            request,
            "tickets/manage_tickets_page_for_specialist.html",
            {"ticket": ticket, "actions": actions},
        )

    if is_program_officer:
        actions.extend(
            ["respond_ticket", "return_to_student", "redirect_ticket", "merge_ticket"]
        )

        specialists = (
            User.objects.filter(role="specialist")
            .annotate(
                open_tickets=Count(
                    "assigned_tickets",
                    filter=Q(assigned_tickets__status="open"),
                )
            )
            .order_by("username", "department", "open_tickets")
        )

        if request.method == "POST":
            action = request.POST.get("action_type")

            if action == "respond_ticket":
                return respond_ticket(request, ticket_id)
            elif action == "redirect_ticket":
                return redirect("redirect_ticket", ticket_id=ticket.id)
            elif action == "merge_ticket":
                return merge_ticket(request, ticket_id=ticket.id)
            elif action == "return_to_student":
                return return_ticket(request, ticket_id=ticket.id)
        activities = (
            TicketActivity.objects.filter(ticket=ticket)
            .select_related("action_by")
            .order_by("-action_time")[:20]
        )

        return render(
            request,
            "tickets/manage_tickets_page_for_program_officer.html",
            {
                "ticket": ticket,
                "actions": actions,
                "activities": activities,
                "specialists": specialists,
            },
        )


@login_required
def submit_ticket(request):
    if request.method == "POST":
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.creator = request.user
            ticket.status = "open"

            # Allow student to select priority
            ticket.priority = form.cleaned_data["priority"]

            # Check for duplicate tickets with the same title
            existing_ticket = Ticket.objects.filter(
                title=ticket.title, status="open"
            ).first()
            if existing_ticket:
                # Merge duplicate ticket descriptions
                existing_ticket.description += (
                    "\n\nMerged with ticket ID: {}. New description: {}".format(
                        ticket.id, ticket.description
                    )
                )
                existing_ticket.save()

                # Log the merge action
                TicketActivity.objects.create(
                    ticket=existing_ticket,
                    action="merged",
                    action_by=request.user,
                    comment=f"Merged with ticket {ticket.id}",
                )

                messages.success(request, f"You have already send the same ticket!")
                return redirect("ticket_detail", ticket_id=existing_ticket.id)
            else:
                # Save the new ticket if it's unique
                ticket.save()

                # Handle file uploads
                files = request.FILES.getlist("file")
                for file in files:
                    TicketAttachment.objects.create(ticket=ticket, file=file)

                # Log ticket creation
                TicketActivity.objects.create(
                    ticket=ticket, action="created", action_by=request.user
                )

                # AI processing (optional)
                ai_process_ticket(ticket)

                # Send confirmation email
                send_ticket_confirmation_email(ticket)

                messages.success(
                    request, "Your ticket has been submitted successfully!"
                )
                return redirect("ticket_detail", ticket_id=ticket.id)
    else:
        form = TicketForm()

    return render(request, "tickets/submit_ticket.html", {"form": form})
