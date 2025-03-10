def respond_to_ticket(request, current_user):
    """处理回复 Ticket"""
    ticket_id = request.POST.get("ticket_id")
    response_message = request.POST.get("response_message")
    ticket = get_object_or_404(Ticket, id=ticket_id)

    ticket.answers = (ticket.answers or "") + f"\nResponse by {current_user.username}: {response_message}"
    ticket.latest_action = 'responded'
    ticket.save()

    TicketActivity.objects.create(ticket=ticket, action='responded', action_by=current_user, comment=response_message)

    return redirect('dashboard_program_officer')


def redirect_ticket(request, current_user):
    """处理 Ticket 重定向"""
    ticket_id = request.POST.get('ticket_id')
    new_assignee_id = request.POST.get('new_assignee_id')
    ticket = get_object_or_404(Ticket, id=ticket_id)
    new_assignee = get_object_or_404(User, id=new_assignee_id)

    ticket.assigned_user = new_assignee
    ticket.latest_action = 'redirected'
    ticket.status = 'in_progress'
    ticket.save()

    TicketActivity.objects.create(ticket=ticket, action='redirected', action_by=current_user, comment=f"Redirected to {new_assignee.username}")

    return redirect('dashboard_program_officer')
