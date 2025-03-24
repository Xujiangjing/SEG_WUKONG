import imaplib
import email
import re
import sys
import requests
from email.header import decode_header
from django.core.management.base import BaseCommand
from tickets.helpers import (
    handle_uploaded_file_in_chunks,
    send_ticket_confirmation_email,
)
from tickets.models import (
    Ticket,
    Department,
    User,
    AITicketProcessing,
    TicketAttachment,
)
from django.conf import settings
from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
import os
from django.db.models import Count
from tickets.ai_service import ai_process_ticket
from django.core.files.base import ContentFile
from django.utils.text import get_valid_filename


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

                try:

                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    for response_part in msg_data:

                        if not isinstance(response_part, tuple):
                            continue
                        payload = response_part[1]
                        msg = email.message_from_bytes(payload)

                        subject, sender_email, body, attachments = (
                            self.parse_email_message(msg)
                        )

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

                        existing_ticket = self.is_duplicate_ticket(
                            sender_email, subject, body
                        )
                        if existing_ticket:
                            self.send_duplicate_notice(
                                sender_email, subject, existing_ticket.id
                            )
                            continue

                        department = self.categorize_ticket(subject, body)
                        ticket = Ticket.objects.create(
                            title=subject,
                            description=body,
                            creator=user,
                            sender_email=sender_email,
                            status="in_progress",
                            assigned_department="general_enquiry",
                        )

                        for attachment in attachments:
                            try:
                                handle_uploaded_file_in_chunks(
                                    ticket,
                                    file_obj=attachment["data"],
                                    filename=attachment["filename"],
                                )
                            except Exception as e:
                                self.stderr.write(
                                    self.style.ERROR(f"❌ Error saving attachment: {e}")
                                )

                        ai_process_ticket(ticket)

                        send_ticket_confirmation_email(ticket)

                        mail.store(email_id, "+FLAGS", "\\Seen")

                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(f"❌ Error processing email: {e}")
                    )

                    mail.store(email_id, "+FLAGS", "\\Seen")
                    continue

            mail.logout()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error fetching emails: {e}"))

    def categorize_ticket(self, subject, body):
        """Assigns a category based on keywords in the subject or body."""

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

        # Check if any keyword is present in the subject or body
        for keyword_pattern, category_name in categories.items():
            if any(
                keyword in subject.lower() or keyword in body.lower()
                for keyword in keyword_pattern.split("|")
            ):
                return Department.objects.filter(name=category_name).first()

        return Department.objects.filter(name="general_enquiry").first()

    def is_duplicate_ticket(self, sender_email, subject, body):
        """
        Checks if a duplicate ticket exists in the last 7 days.
        - It allows resubmission if no response is received within 7 days.
        """
        time_threshold = now() - timedelta(days=7)
        # search for an old ticket with the same details
        old_ticket = (
            Ticket.objects.annotate(response_count=Count("responses"))
            .filter(
                sender_email=sender_email.strip(),
                title__iexact=subject.strip(),
                description__iexact=body.strip(),
                created_at__lt=time_threshold,  # 7 days ago
            )
            .order_by("-created_at")
            .first()
        )

        if old_ticket:
            if (
                old_ticket.response_count == 0
            ):  # Allow resubmission if no response over 7 days
                return None
            else:
                self.send_duplicate_notice(
                    sender_email, subject, old_ticket.id
                )  # Notify student
                return old_ticket  # Reject resubmission if there is a response even after 7 days

        # Search for a recent ticket within 7 days
        recent_ticket = (
            Ticket.objects.filter(
                sender_email=sender_email.strip(),
                title__iexact=subject.strip(),
                description__iexact=body.strip(),
                created_at__gte=time_threshold,  # within 7 days
            )
            .order_by("-created_at")
            .first()
        )

        if recent_ticket:
            self.send_duplicate_notice(
                sender_email, subject, recent_ticket.id
            )  # Notify student
            return recent_ticket  # Check for a recent ticket within 7 days

        return None  # No duplicate ticket found

    def send_duplicate_notice(self, student_email, ticket_title, ticket_id):
        """
        Sends an email notifying the student that their ticket is a duplicate.
        """
        subject = f"Duplicate Ticket Submission - {ticket_title}"
        message = f"""
        Hello,

        You have already submitted a ticket with the same details: '{ticket_title}'.
        You can track it using Ticket ID #{ticket_id}.

        Our team is currently working on it. Please wait for a response before submitting again.
        If no response is received within 7 days, you may resubmit.

        Thank you for your patience.

        Regards,
        WuKong Help Desk 
        """
        send_mail(subject, message, settings.EMAIL_HOST_USER, [student_email])

    def is_spam(self, subject, body):
        """Uses Google's Perspective API to detect spam."""
        if settings.TESTING:
            return False

        PERSPECTIVE_API_KEY = settings.PERSPECTIVE_API_KEY

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
            response.raise_for_status()  # check for any request errors
            result = response.json()

            # Check if the spam score is above the threshold
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
        """Parses subject, sender, body, and attachments (robust version)."""

        try:
            # Decode subject
            subject = ""
            for part, encoding in decode_header(msg.get("Subject", "")):
                try:
                    if isinstance(part, bytes):
                        subject += part.decode(encoding or "utf-8", errors="ignore")
                    elif isinstance(part, str):
                        subject += part
                    else:
                        subject += str(part)
                except Exception as e:
                    print("❌ Error decoding subject part:", e)

            # Extract sender
            sender = msg.get("From", "")
            match = re.search(r"<(.+?)>", sender)
            sender_email = match.group(1) if match else sender

            body = ""
            attachments = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))

                    # Body
                    if (
                        content_type == "text/plain"
                        and "attachment" not in content_disposition
                    ):
                        part_payload = part.get_payload(decode=True)
                        try:
                            if isinstance(part_payload, bytes):
                                body = part_payload.decode("utf-8", errors="ignore")
                            elif isinstance(part_payload, str):
                                body = part_payload
                            else:
                                body = str(part_payload)
                        except Exception as e:

                            body = "[Decode Error]"

                    # Attachment
                    elif "attachment" in content_disposition:
                        filename = part.get_filename()

                        if filename:
                            decoded_filename = ""
                            for p, enc in decode_header(filename):

                                try:
                                    if isinstance(p, bytes):
                                        decoded_filename += p.decode(
                                            enc or "utf-8", errors="ignore"
                                        )
                                    elif isinstance(p, str):
                                        decoded_filename += p
                                    else:
                                        decoded_filename += str(p)
                                except Exception as e:
                                    print("❌ Error decoding attachment filename:", e)
                            file_data = part.get_payload(decode=True)

                            if not isinstance(file_data, (bytes, str)):

                                continue
                            attachments.append(
                                {
                                    "filename": decoded_filename,
                                    "content_type": content_type,
                                    "data": file_data,
                                }
                            )

            else:
                payload = msg.get_payload(decode=True)
                try:
                    if isinstance(payload, bytes):
                        body = payload.decode("utf-8", errors="ignore")
                    elif isinstance(payload, str):
                        body = payload
                    else:
                        body = str(payload)
                except Exception as e:

                    body = "[Decode Error]"

            return subject, sender_email, body, attachments

        except Exception as e:
            print("❌ Error parsing email message:", e)
            return "", "", "", []
