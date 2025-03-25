import os
import boto3
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib import messages
from django.core.files.uploadedfile import SimpleUploadedFile
from moto import mock_aws
from tickets.models import User, Ticket, TicketAttachment
from tickets.forms import TicketForm
import json


@mock_aws
@override_settings(
    AWS_ACCESS_KEY_ID="fake_access_key",
    AWS_SECRET_ACCESS_KEY="fake_secret_key",
    AWS_S3_REGION_NAME="eu-west-2",
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_DEFAULT_ACL=None,
)
class CreateTicketViewTestCase(TestCase):
    fixtures = [
        "tickets/tests/fixtures/default_user.json",
    ]

    def setUp(self):
        self.s3_client = boto3.client('s3', region_name='eu-west-2')
        self.s3_client.create_bucket(
            Bucket='test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'}
        )
        self.s3_client.put_bucket_acl(Bucket='test-bucket', ACL='public-read-write')
        self.user = User.objects.get(username='@johndoe')
        self.user.role = 'students'
        self.user.save()
        self.url = reverse('create_ticket')
        self.form_input = {
            'title': 'My Test Ticket',
            'description': 'Hello, I have an issue with my coursework.',
            'priority': 'medium'
        }


    def test_create_ticket_url(self):
        self.assertEqual(self.url, "/tickets/create/")

    def test_post_create_ticket_as_student(self):
        self.client.login(username=self.user.username, password="Password123")

        form_input_student = {
            "title": "Student Ticket",
            "description": "I am a student, I want medium priority!",
            "priority": "medium",
        }
        before_count = Ticket.objects.count()
        response = self.client.post(self.url, form_input_student, follow=True)
        after_count = Ticket.objects.count()
        self.assertEqual(after_count, before_count + 1)

        ticket = Ticket.objects.latest("created_at")
        self.assertEqual(ticket.title, form_input_student["title"])
        self.assertEqual(ticket.description, form_input_student["description"])
        # Force to 'low' if user is a student
        self.assertEqual(ticket.priority, "low")
        self.assertEqual(ticket.assigned_department, "general_enquiry")
        self.assertEqual(ticket.creator, self.user)

        response_data = json.loads(response.content)
        expected_redirect_url = reverse(
            "ticket_detail", kwargs={"ticket_id": ticket.pk}
        )
        self.assertEqual(response_data["redirect_url"], expected_redirect_url)

        messages_list = list(response.wsgi_request._messages)
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(messages_list[0].level, messages.SUCCESS)

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.url)
        login_url = reverse("log_in")
        self.assertRedirects(
            response,
            f"{login_url}?next={self.url}",
            status_code=302,
            target_status_code=200,
        )

    def test_get_create_ticket_view_when_logged_in(self):
        self.client.login(username=self.user.username, password="Password123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tickets/create_ticket.html")

        form = response.context["form"]
        self.assertTrue(isinstance(form, TicketForm))
        self.assertFalse(form.is_bound)

    def test_post_create_ticket_valid_data(self):
        self.client.login(username=self.user.username, password="Password123")
        before_count = Ticket.objects.count()

        response = self.client.post(self.url, self.form_input, follow=True)
        after_count = Ticket.objects.count()
        self.assertEqual(after_count, before_count + 1)

        ticket = Ticket.objects.latest("created_at")
        self.assertEqual(ticket.title, self.form_input["title"])
        self.assertEqual(ticket.description, self.form_input["description"])

        # Because user is student, priority is forced to 'low'
        self.assertEqual(ticket.priority, "low")
        self.assertEqual(ticket.assigned_department, "general_enquiry")
        self.assertEqual(ticket.creator, self.user)

        response_data = json.loads(response.content)
        expected_redirect_url = reverse(
            "ticket_detail", kwargs={"ticket_id": ticket.pk}
        )
        self.assertEqual(response_data["redirect_url"], expected_redirect_url)

        messages_list = list(response.wsgi_request._messages)
        self.assertEqual(len(messages_list), 1)
        self.assertEqual(messages_list[0].level, messages.SUCCESS)




    def test_post_create_ticket_invalid_data(self):
        self.client.login(username=self.user.username, password="Password123")

        invalid_input = {
            "title": "",
            "description": "No Title Provided",
            "priority": "medium",
        }
        before_count = Ticket.objects.count()
        response = self.client.post(self.url, invalid_input)
        after_count = Ticket.objects.count()
        self.assertEqual(after_count, before_count)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tickets/create_ticket.html")

        form = response.context["form"]
        self.assertTrue(isinstance(form, TicketForm))
        self.assertTrue(form.is_bound)
        self.assertFalse(form.is_valid())

        messages_list = list(response.wsgi_request._messages)
        self.assertEqual(len(messages_list), 0)
