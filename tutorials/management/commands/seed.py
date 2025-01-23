from django.core.management.base import BaseCommand, CommandError
from tutorials.models import User, Department
import pytz
from faker import Faker
import random

user_fixtures = [
    {'username': '@johndoe', 'email': 'john.doe@example.org', 'first_name': 'John', 'last_name': 'Doe', 'role': 'students'},
    {'username': '@janedoe', 'email': 'jane.doe@example.org', 'first_name': 'Jane', 'last_name': 'Doe', 'role': 'specialists'},
    {'username': '@charlie', 'email': 'charlie.johnson@example.org', 'first_name': 'Charlie', 'last_name': 'Johnson', 'role': 'program_officers'},
]


class Command(BaseCommand):
    """Build automation command to seed the database."""

    USER_COUNT = 300
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
        self.generate_user_fixtures()
        self.generate_random_users()

    def generate_user_fixtures(self):
        for data in user_fixtures:
            department = None
            if data['role'] == 'specialists':    
                specialist_departments = Department.objects.filter(responsible_roles__icontains='specialists')
                if specialist_departments.exists():
                    department = random.choice(specialist_departments)
            elif data['role'] == 'program_officers':
                program_officers_departments = Department.objects.filter(responsible_roles__icontains='program_officers')
                
            self.try_create_user(data, department)


    def generate_random_users(self):
        user_count = User.objects.count()
        while  user_count < self.USER_COUNT:
            print(f"Seeding user {user_count}/{self.USER_COUNT}", end='\r')
            self.generate_user()
            user_count = User.objects.count()
        print("User seeding complete.      ")

    def generate_user(self):
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

        self.try_create_user({'username': username, 'email': email, 'first_name': first_name, 'last_name': last_name, 'role': role}, department)
       
    def try_create_user(self, data, department=None):
        try:
            if 'role' not in data:  # Default to 'others', this is for the admin, superuser.
                data['role'] = 'others'
            self.create_user(data, department)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating user {data['username']}: {e}"))

    def create_user(self, data, department=None):
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

def create_username(first_name, last_name):
    return '@' + first_name.lower() + last_name.lower()

def create_email(first_name, last_name):
    return first_name + '.' + last_name + '@example.org'
