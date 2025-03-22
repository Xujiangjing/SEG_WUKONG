import os
import uuid

import boto3
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.timezone import now
from moto import mock_s3

from django.core.files.uploadedfile import SimpleUploadedFile
from tickets.models import AITicketProcessing, User, Department, Ticket, TicketAttachment
from tickets.views import handle_uploaded_file_in_chunks

@mock_s3
@override_settings(
    AWS_ACCESS_KEY_ID="fake_access_key",
    AWS_SECRET_ACCESS_KEY="fake_secret_key",
    AWS_STORAGE_BUCKET_NAME="test-bucket",
    AWS_S3_REGION_NAME="us-east-1",
    AWS_DEFAULT_ACL=None,
)
class S3AttachmentURLDownloadTestCase(TestCase):

    def setUp(self):
        
        self.s3_client = boto3.client("s3", region_name="us-east-1")
        self.s3_client.create_bucket(Bucket="test-bucket")

        
        self.department = Department.objects.create(
            name="it_support",
            description="IT department",
        )

        
        self.student_user = User.objects.create_user(
            username="@student",
            password="Password123",
            role="students",
            email="student@example.org",
            department=None,
        )
        
        self.specialist_user = User.objects.create_user(
            username="@specialist",
            password="Password123",
            role="specialists",
            email="spec@example.org",
            department=self.department,
        )
        
        self.program_officer_user = User.objects.create_user(
            username="@po",
            password="Password123",
            role="program_officers",
            email="po@example.org",
            department=self.department,
        )


        self.ticket = Ticket.objects.create(
            creator=self.student_user,
            title="Test Ticket With Attachments",
            description="Ticket Description for S3 attachments test",
            status="open",
            assigned_department=self.department.name,
            assigned_user=self.specialist_user,
        )
        
        AITicketProcessing.objects.create(
            ticket=self.ticket,
            ai_assigned_department='it_support'
        )



        test_file1 = SimpleUploadedFile(
            "example1.txt",
            b"Hello S3 Attachment 1",
            content_type="text/plain",
        )
        handle_uploaded_file_in_chunks(self.ticket, test_file1)

        test_file2 = SimpleUploadedFile(
            "example2.txt",
            b"Hello S3 Attachment 2",
            content_type="text/plain",
        )
        handle_uploaded_file_in_chunks(self.ticket, test_file2)

        
        #    - ticket_detail
        self.ticket_detail_url = reverse("ticket_detail", kwargs={"ticket_id": self.ticket.id})
        #    - respond_ticket_page
        self.respond_ticket_page_url = reverse("respond_ticket_page", kwargs={"ticket_id": self.ticket.id})
        #    - return_ticket_page
        self.return_ticket_page_url = reverse("return_ticket_page", kwargs={"ticket_id": self.ticket.id})
        #    - update_ticket_page
        self.update_ticket_page_url = reverse("update_ticket_page", kwargs={"ticket_id": self.ticket.id})
        #    - redirect_ticket_page
        self.redirect_ticket_page_url = reverse("redirect_ticket_page", kwargs={"ticket_id": self.ticket.id})

    def test_ticket_detail_shows_attachments(self):

        self.client.login(username="@student", password="Password123")
        response = self.client.get(self.ticket_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "example1.txt")
        self.assertContains(response, "example2.txt")

    def test_respond_ticket_page_shows_attachments(self):

        self.client.login(username="@specialist", password="Password123")
        response = self.client.post(self.respond_ticket_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "example1.txt")
        self.assertContains(response, "example2.txt")

    def test_return_ticket_page_shows_attachments(self):
        
        self.client.login(username="@po", password="Password123")
        response = self.client.post(self.return_ticket_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "example1.txt")
        self.assertContains(response, "example2.txt")

    def test_update_ticket_page_shows_attachments(self):
        
        self.client.login(username="@student", password="Password123")
        response = self.client.get(self.update_ticket_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "example1.txt")
        self.assertContains(response, "example2.txt")

    def test_redirect_ticket_page_shows_attachments(self):
        
        self.client.login(username="@po", password="Password123")
        response = self.client.get(self.redirect_ticket_page_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "example1.txt")
        self.assertContains(response, "example2.txt")