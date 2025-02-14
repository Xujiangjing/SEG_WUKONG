import imaplib
import email
import re
from email.header import decode_header
from django.core.management.base import BaseCommand
from tickets.models import Ticket, Department, User, AITicketProcessing
from django.conf import settings
from django.core.mail import send_mail
from tickets.ai_service import generate_ai_answer, classify_department


class Command(BaseCommand):
    help = "Fetch unread emails from Gmail and convert them into tickets"

    def handle(self, *args, **kwargs):
        try:
            # Connect to Gmail IMAP server
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login("wukonghelpdesk@gmail.com", "bynw apnb vmuu nmun")
            mail.select("inbox")  # Select the inbox

            # Search for unread emails
            status, messages = mail.search(None, "UNSEEN")
            email_ids = messages[0].split()

            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])

                        # Decode email subject
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")

                        sender = msg.get("From")
                        
                        # Extract the sender's email address
                        match = re.search(r"<(.+?)>", sender)
                        sender_email = match.group(1) if match else sender

                        # filter out failure notifications
                        if "mailer-daemon" in sender_email.lower() or "delivery status notification" in subject.lower():
                            self.stdout.write(self.style.WARNING(f"⚠️ Skipping failure notification from {sender_email}: {subject}"))
                            continue
                        
                        body = ""

                        # Extract the email body
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    body = part.get_payload(decode=True)
                                    if isinstance(body, bytes):  # make sure it's a string
                                        body = body.decode("utf-8", errors="ignore")
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                            
                        assigned_department = self.categorize_ticket(subject, body)
                        
                        # revise the code to create a new user if the sender is not in the database
                        user = User.objects.filter(email=sender_email).first()
                        if not user:
                            user = User.objects.create(username=sender_email.split("@")[0], email=sender_email, password="TemporaryPass123")
                            self.stdout.write(self.style.WARNING(f"⚠️ Created new user for {sender_email}"))

                        # create a new ticket
                        ticket = Ticket.objects.create(
                            title=subject,
                            description=body,
                            creator=user,
                            sender_email=sender_email,
                            status="open",
                            assigned_department=assigned_department
                        )

                        ai_department = classify_department(ticket.description)
                        ai_answer = generate_ai_answer(ticket.description)
                        AITicketProcessing.objects.create(
                            ticket=ticket,
                            ai_generated_answer=ai_answer,
                            ai_assigned_department=ai_department
                        )

                        # send a confirmation email to the student
                        self.send_confirmation_email(sender_email, subject)

                        # print a success message
                        self.stdout.write(self.style.SUCCESS(f"🎫 Ticket created from email: {subject}"))

                        # mark the email as read
                        mail.store(email_id, "+FLAGS", "\\Seen")

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
            if any(keyword in subject.lower() or keyword in body.lower() for keyword in keyword_pattern.split("|")):
                return Department.objects.filter(name=category_name).first()
            

        return Department.objects.filter(name="general_enquiry").first()
    
    def send_confirmation_email(self, student_email, ticket_title):
        """Sends a confirmation email to the student with a signature, school logo, and styled font."""
        
        subject = f"Your Ticket '{ticket_title}' Has Been Received"
        
        # HTML Email Content
        # 吗的彩色的Logo和Signature打不出来 需要替换成其他的
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; text-align: center;">
                <div style="border: 1px solid #ddd; padding: 20px; border-radius: 10px; max-width: 600px; margin: auto;">
        
                    <!-- WUKONG Logo with Gradient Background -->
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

                    <!-- Signature Part -->
                    <p style="border-top: 2px solid #0056b3; padding-top: 10px; font-size: 14px; text-align: left; line-height: 1.6;">
                        <strong>Best regards,</strong><br>

                        <!-- WuKong Help Desk Gradient -->
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
    
        # Sending email with HTML content
        send_mail(
            subject,
            message="",  # Leave plain text empty
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[student_email],
            fail_silently=False,
            html_message=html_message,  # Use the HTML content
        )

        self.stdout.write(self.style.SUCCESS(f"📧 Confirmation email sent to {student_email}"))