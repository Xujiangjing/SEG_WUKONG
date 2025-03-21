import imaplib
import email
import re
import sys
import requests
from email.header import decode_header
from django.core.management.base import BaseCommand
from tickets.models import Ticket, Department, User, AITicketProcessing, TicketAttachment
from django.conf import settings
from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
import os
from django.db.models import Count
from tickets.ai_service import ai_process_ticket
from django.core.files.base import ContentFile


class Command(BaseCommand):
    help = "Fetch unread emails from Gmail and convert them into tickets"

    def handle(self, *args, **kwargs):
        try:
            mail = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
            mail.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            mail.select("inbox") 

            status, messages = mail.search(None, "UNSEEN")
            email_ids = messages[0].split()

            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                for response_part in msg_data:
                    if not isinstance(response_part, tuple):
                        continue
                    payload = response_part[1]
                    msg = email.message_from_bytes(payload)

                    subject, sender_email, body = self.parse_email_message(msg)

                    if (
                        "mailer-daemon" in sender_email.lower()
                        or "delivery status notification" in subject.lower()
                    ):
                        continue

                    user, created = User.objects.get_or_create(
                        email=sender_email,
                        defaults={
                            "username": sender_email.split("@")[0],
                            "password": "TemporaryPass123",
                        },
                    )
                    if created:
                        user.set_password("TemporaryPass123")
                        user.save()

                    if self.is_spam(subject, body):
                        continue
                    existing_ticket = self.is_duplicate_ticket(sender_email, subject, body)
                    if existing_ticket:
                        self.send_duplicate_notice(sender_email, subject, existing_ticket.id)
                        continue


                    department = self.categorize_ticket(subject, body)


                    ticket = Ticket.objects.create(
                        title=subject,
                        description=body,
                        creator=user,
                        sender_email=sender_email,
                        status="in_progress",
                        assigned_department=department,
                    )

                    for part in msg.walk():
                        if part.get_content_maintype() == "multipart":
                            continue
                        content_disposition = str(part.get("Content-Disposition") or "")
                        if "attachment" in content_disposition.lower():
                            attachment_data = part.get_payload(decode=True)
                            filename = part.get_filename()
                            if filename and attachment_data:

                                attachment = TicketAttachment(ticket=ticket)

                                attachment.file.save(
                                    filename,
                                    ContentFile(attachment_data),
                                    save=True
                                )

                    ai_process_ticket(ticket)

                    self.send_confirmation_email(sender_email, subject)

                    mail.store(email_id, "+FLAGS", "\\Seen")

            mail.logout()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error fetching emails: {e}"))

    def _handle_attachments(self, msg, ticket):
        """
        Walk through the MIME parts of 'msg' and save any attachments to TicketAttachment.
        """
        if not msg.is_multipart():
            # No attachments if not multipart
            return

        for part in msg.walk():
            content_disposition = part.get("Content-Disposition", None)
            if content_disposition and "attachment" in content_disposition.lower():
                file_data = part.get_payload(decode=True)
                filename = part.get_filename()
                if not filename:
                    filename = "unknown_attachment"

                if file_data:
                    # Wrap the file data in a Django ContentFile
                    django_file = ContentFile(file_data)

                    # Create a TicketAttachment and save
                    attachment = TicketAttachment(ticket=ticket)
                    attachment.file.save(filename, django_file, save=True)

    def categorize_ticket(self, subject, body):
        """Assign a category based on keywords in subject or body."""
        categories = {
            "general": "general_enquiry",
            "course|academic|exam|grades|study": "academic_support",
            "health|medical|doctor|sick|hospital": "health_services",
            "financial|payment|tuition|scholarship": "financial_aid",
            "career|job|internship|resume": "career_services",
            "welfare|counseling|support": "welfare",
            "misconduct|disciplinary|plagiarism": "misconduct",
            "wifi|login|it support|computer|software": "it_support",
            "housing|accommodation|dorm|rent": "housing",
            "admissions|application|enrollment": "admissions",
            "library|books|borrowing|overdue": "library_services",
            "research|thesis|proposal|publication": "research_support",
            "study abroad|exchange|visa": "study_abroad",
            "alumni|graduate|networking": "alumni_relations",
            "exam|grades|schedule|timetable": "exam_office",
            "security|crime|theft|safety": "security",
            "language|english|spanish|french": "language_centre",
        }
        subject_lower = subject.lower()
        body_lower = body.lower()
        for pattern, dept_name in categories.items():
            if any(k in subject_lower or k in body_lower for k in pattern.split("|")):
                return Department.objects.filter(name=dept_name).first()

        return Department.objects.filter(name="general_enquiry").first()

    def send_confirmation_email(self, student_email, ticket_title):
        """Send a confirmation email to the student with stylized HTML content."""
        subject = f"Your Ticket '{ticket_title}' Has Been Received"
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; text-align: center;">
                <div style="border: 1px solid #ddd; padding: 20px; border-radius: 10px; max-width: 600px; margin: auto;">
                    <h1 style="font-size: 32px; font-weight: bold; display: inline-block;
                               background: linear-gradient(90deg, red, orange, yellow, green, blue, indigo, violet);
                               color: white; padding: 10px 20px; border-radius: 5px;">
                        WUKONG
                    </h1>
                    <h2 style="text-align: center; color: #0056b3;">Your Ticket Has Been Received</h2>
                    <p style="text-align: left;">Hello,</p>
                    <p style="text-align: left;">Thank you for reaching out. Your ticket titled <b>'{ticket_title}'</b> has been received and assigned to the relevant department.</p>
                    <p style="text-align: left;">We will get back to you as soon as possible.</p>
                    <br>
                    <p style="border-top: 2px solid #0056b3; padding-top: 10px; font-size: 14px; text-align: left; line-height: 1.6;">
                        <strong>Best regards,</strong><br>
                        <span style="font-size: 16px; font-weight: bold; display: inline-block; margin-top: 5px;
                                     background: linear-gradient(90deg, red, orange, yellow, green, blue, indigo, violet);
                                     color: white; padding: 3px 8px; border-radius: 5px;">
                            WuKong Help Desk
                        </span>
                        <br><br>
                        <span style="color: #007BFF;"><strong>Email:</strong></span>
                        <a href="mailto:wukonghelpdesk@gmail.com" style="color: #007BFF; text-decoration: none;">wukonghelpdesk@gmail.com</a><br>
                        <span style="color: #28A745;"><strong>Phone:</strong></span>
                        <span style="color: #28A745;">+1 (234) 567-890</span><br>
                        <span style="color: #DC3545;"><strong>Website:</strong></span>
                        <a href="https://github.com/Haichong0-0/WUKONG" style="color: #DC3545; text-decoration: none;">https://github.com/Haichong0-0/WUKONG</a>
                    </p>
                </div>
            </body>
        </html>
        """
        send_mail(
            subject=subject,
            message="",  # Plain text left empty
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[student_email],
            fail_silently=False,
            html_message=html_message,
        )

    def is_duplicate_ticket(self, sender_email, subject, body):
        """
        Checks if a duplicate ticket exists in the last 7 days.
        Allows resubmission if no response is received within 7 days.
        """
        time_threshold = now() - timedelta(days=7)
        old_ticket = (
            Ticket.objects.annotate(response_count=Count("responses"))
            .filter(
                sender_email=sender_email.strip(),
                title__iexact=subject.strip(),
                description__iexact=body.strip(),
                created_at__lt=time_threshold,
            )
            .order_by("-created_at")
            .first()
        )
        if old_ticket:
            if old_ticket.response_count == 0:
                return None
            else:
                self.send_duplicate_notice(sender_email, subject, old_ticket.id)
                return old_ticket

        # Check recent tickets within 7 days
        recent_ticket = (
            Ticket.objects.filter(
                sender_email=sender_email.strip(),
                title__iexact=subject.strip(),
                description__iexact=body.strip(),
                created_at__gte=time_threshold,
            )
            .order_by("-created_at")
            .first()
        )
        if recent_ticket:
            self.send_duplicate_notice(sender_email, subject, recent_ticket.id)
            return recent_ticket

        return None

    def send_duplicate_notice(self, student_email, ticket_title, ticket_id):
        """
        Sends an email notifying the student that their ticket is a duplicate.
        """
        subject = f"Duplicate Ticket Submission - {ticket_title}"
        message = f"""
        Hello,

        You have already submitted a ticket with the same details: '{ticket_title}'.
        Ticket ID: {ticket_id}.

        Our team is currently working on it. Please wait for a response before submitting again.
        If no response is received within 7 days, you may resubmit.

        Thank you for your patience.

        Regards,
        WuKong Help Desk
        """
        send_mail(subject, message, settings.EMAIL_HOST_USER, [student_email], fail_silently=False)

    def is_spam(self, subject, body):
        """Uses Google's Perspective API to detect spam (optional)."""
        if settings.TESTING:
            return False

        PERSPECTIVE_API_KEY = settings.PERSPECTIVE_API_KEY
        if not PERSPECTIVE_API_KEY:
            return False  # If API key is not set, skip spam check

        url = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
        content = f"{subject} {body}"
        data = {
            "comment": {"text": content},
            "requestedAttributes": {"TOXICITY": {}, "SPAM": {}},
            "languages": ["en"],
            "doNotStore": True,
        }
        try:
            response = requests.post(f"{url}?key={PERSPECTIVE_API_KEY}", json=data)
            response.raise_for_status()
            result = response.json()
            spam_score = (
                result.get("attributeScores", {})
                .get("SPAM", {})
                .get("summaryScore", {})
                .get("value", 0)
            )
            return spam_score > 0.8
        except requests.RequestException as e:
            print("❌ Error connecting to Perspective API:", e)
            return False
        except ValueError:
            print("❌ Invalid JSON response from Perspective API")
            return False

    def parse_email_message(self, msg):
        """Decodes email subject, extracts sender email, and returns plaintext body."""
        subject = ""
        raw_subject = msg.get("Subject", "")
        for part, encoding in decode_header(raw_subject):
            if isinstance(part, bytes):
                subject += part.decode(encoding or "utf-8", errors="ignore")
            else:
                subject += part

        sender = msg.get("From", "")
        match = re.search(r"<(.+?)>", sender)
        sender_email = match.group(1) if match else sender

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition") or "")
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    decoded_part = part.get_payload(decode=True)
                    if decoded_part:
                        body = decoded_part.decode("utf-8", errors="ignore")
                    break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")

        return subject, sender_email, body