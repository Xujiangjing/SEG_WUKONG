import random
import time
import re
import os

import pytz
from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.core.management.base import BaseCommand, CommandError
from faker import Faker
from tickets.models import Department, Ticket, User, AITicketProcessing
from tickets.ai_service import generate_ai_answer, classify_department, query_bedrock
import boto3
from botocore.exceptions import ClientError
import json


user_fixtures = [
    {'username': '@johndoe', 'email': 'john.doe@example.org', 'first_name': 'John', 'last_name': 'Doe', 'role': 'students'},
    {'username': '@janedoe', 'email': 'jane.doe@example.org', 'first_name': 'Jane', 'last_name': 'Doe', 'role': 'specialists'},
    {'username': '@charlie', 'email': 'charlie.johnson@example.org', 'first_name': 'Charlie', 'last_name': 'Johnson', 'role': 'program_officers'},
]

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

class Command(BaseCommand):
    """Build automation command to seed the database."""
    TICKET_COUNT = 5
    USER_COUNT = 30
    DEFAULT_PASSWORD = 'Password123'
    help = 'Seeds the database with sample data'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.faker = Faker('en_GB')

    def handle(self, *args, **options):
        # Seed Departments
        self.seed_departments()

        # Seed Users
        self.create_users()
    
        # Seed Tickets
        self.create_tickets()
        
    def send_bulk_emails(self, users):
        connection = get_connection()
        students = list(User.objects.filter(role='students'))
        selected_students = random.sample(students, min(5, len(students)))
        for user in selected_students:
            try:
                self.send_welcome_email(user, connection)
                time.sleep(2)  
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error sending email to {user.email}: {e}"))

        connection.close()
        
        self.create_tickets()
    
    def seed_departments(self):
        departments = [
            {'name': 'general_enquiry', 'description': 'General queries managed by program officers.', 'responsible_roles': 'program_officers'},
            {'name': 'academic_support', 'description': 'Academic support provided by personal tutors.', 'responsible_roles': 'specialists'},
            {'name': 'health_services', 'description': 'Health-related issues handled by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'financial_aid', 'description': 'Financial aid inquiries managed by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'career_services', 'description': 'Career guidance provided by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'welfare', 'description': 'Welfare support provided by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'misconduct', 'description': 'Misconduct cases managed by personal tutors.', 'responsible_roles': 'specialists'},
            {'name': 'it_support', 'description': 'IT-related issues handled by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'housing', 'description': 'Housing queries handled by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'admissions', 'description': 'Admissions queries managed by program officers.', 'responsible_roles': 'program_officers'},
            {'name': 'library_services', 'description': 'Library-related support by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'research_support', 'description': 'Research-related assistance by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'study_abroad', 'description': 'Study abroad support managed by personal tutors.', 'responsible_roles': 'specialists'},
            {'name': 'alumni_relations', 'description': 'Alumni relations managed by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'exam_office', 'description': 'Examination office queries handled by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'security', 'description': 'Campus security issues handled by specialists.', 'responsible_roles': 'specialists'},
            {'name': 'language_centre', 'description': 'Language centre support provided by specialists.', 'responsible_roles': 'specialists'},
        ]

        for department_data in departments:
            department, created = Department.objects.get_or_create(name=department_data['name'], defaults=department_data)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Department '{department.name}' created."))
            else:
                self.stdout.write(self.style.WARNING(f"Department '{department.name}' already exists."))

    def create_users(self):
        connection = get_connection() # Use default email connection
        self.generate_user_fixtures(connection)
        self.generate_random_users(connection)
        
        # Send welcome emails to students
        # users = User.objects.filter(role="students") 
        # self.send_bulk_emails(users)

        connection.close()

    def generate_user_fixtures(self, connection = None):
        for data in user_fixtures:
            department = None
            if data['role'] == 'specialists':    
                specialist_departments = Department.objects.filter(responsible_roles__icontains='specialists')
                if specialist_departments.exists():
                    department = random.choice(specialist_departments)
            elif data['role'] == 'program_officers':
                    department = Department.objects.get(name="general_enquiry")
            self.try_create_user(data, department)

    def generate_random_users(self, connection=None):
        user_count = User.objects.count()
        while  user_count < self.USER_COUNT:
            print(f"Seeding user {user_count}/{self.USER_COUNT}", end='\r')
            self.generate_user(connection)
            user_count = User.objects.count()
        print("User seeding complete.      ")

    def generate_user(self, connection=None):
        first_name = self.faker.first_name()
        last_name = self.faker.last_name()
        email = create_email(first_name, last_name)
        username = create_username(first_name, last_name)

        # Ensure unique email
        while User.objects.filter(email=email).exists():
            email = create_email(first_name, last_name)

        role = self.faker.random_element(['students', 'program_officers', 'specialists'])
        department = None

        # Only assign department to specialists
        if role == 'specialists':
            department = Department.objects.filter(responsible_roles__icontains='specialists')
            if department.exists():
                department = random.choice(department)

        self.stdout.write(self.style.SUCCESS(f"Seeding user: {username} with role: {role}"))
        self.try_create_user({'username': username, 'email': email, 'first_name': first_name, 'last_name': last_name, 'role': role}, department)
    
    def try_create_user(self, data, department=None, connection=None):
        try:
            if 'role' not in data:  # Default to 'others', this is for the admin, superuser.
                data['role'] = 'others'
            self.create_user(data, department, connection)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating user {data['username']}: {e}"))

    def send_welcome_email(self, user, connection=None):
        subject = f"Welcome, {user.first_name}!"
        message = f"""
        Hello {user.first_name},

        Your university account has been created successfully.

        Username: {user.username}
        Email: {user.email}
        Password: {Command.DEFAULT_PASSWORD} (Please change it after login)

        You can log in to the system and manage your tickets.

        Regards,
        WuKong Help Desk
        """
        try:
            send_mail(
                subject, 
                message, 
                settings.EMAIL_HOST_USER, 
                [user.email], 
                connection=connection  
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Email sent to {user.email}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error sending email to {user.email}: {e}"))  # ✅ 记录详细错误
     
    def create_user(self, data, department=None, connection=None):
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=Command.DEFAULT_PASSWORD,
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data.get('role', 'others'), # Default to 'others'
        )
        if department:
            user.department = department
            user.save()
    
    def create_tickets(self):
        """Generate meaningful tickets for students using AWS Bedrock."""
        students = list(User.objects.filter(role='students'))
        if not students:
            self.stdout.write(self.style.WARNING("No students found, skipping ticket creation."))
            return

        departments = list(Ticket.DEPARTMENT_CHOICES)
        new_tickets = []
        new_ai_tickets = []

        while len(new_tickets) < self.TICKET_COUNT:
            student = random.choice(students)
            department = random.choice(departments)[0]

            # Prompt for student query generation
            prompt = f"Create a meaningful/realistic university student query with a title and a description for the {department} department. 50 words max. Answer in a paragraph, do not involve quotation marks or words like: 1.Here is a university student query for the study_abroad department: 2.title/description, just keep the query itself. The first sentence should be the title of the query, the rest should be the description. Separate the title and description with a period."
            ai_generated_query = query_bedrock(prompt)

            if not ai_generated_query:
                continue

            match = re.match(r"^(.*?[.?!])\s*(.*)", ai_generated_query.strip())
            if match:
                title = match.group(1).strip()
                description = match.group(2).strip() or "Further details required."
            else:
                title = ai_generated_query.strip()
                description = "Further details required."
            
            ticket = Ticket(
                creator=student,
                title=title,
                description=description,
                status='open',
                priority=random.choice(['low', 'medium', 'high', 'urgent']),
            )
            new_tickets.append(ticket)
        
        created_tickets = Ticket.objects.bulk_create(new_tickets)
        self.stdout.write(self.style.SUCCESS(f"Successfully created {len(created_tickets)} tickets."))

        for ticket in created_tickets:
            ai_department = classify_department(ticket.description)
            ai_answer = generate_ai_answer(ticket.description)

            ai_ticket = AITicketProcessing.objects.create(
                ticket=ticket,
                ai_generated_response=ai_answer,
                ai_assigned_department=ai_department
            )
            new_ai_tickets.append(ai_ticket)
            self.stdout.write(self.style.SUCCESS(f"Ticket title: {ticket.title}"))
            self.stdout.write(self.style.SUCCESS(f"Description: {ticket.description}"))
            self.stdout.write(self.style.SUCCESS(f"   "))
            self.stdout.write(self.style.SUCCESS(f"AI Response: {ai_answer}"))
            self.stdout.write(self.style.SUCCESS(f"==============================================================================="))
            self.stdout.write(self.style.SUCCESS(f"==============================================================================="))
            self.stdout.write(self.style.SUCCESS(f"   "))
        self.stdout.write(self.style.SUCCESS(f"Successfully answered {len(new_ai_tickets)} tickets."))

def create_username(first_name, last_name):
    return '@' + first_name.lower() + last_name.lower()

def create_email(first_name, last_name):
    return first_name + '.' + last_name + '@example.org'

