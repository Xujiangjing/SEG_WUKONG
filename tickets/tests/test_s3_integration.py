import boto3
from unittest import TestCase
from django.test import override_settings
from moto import mock_s3
from django.test import TestCase  
from django.core.files.uploadedfile import SimpleUploadedFile
from storages.backends.s3boto3 import S3Boto3Storage

@mock_s3
@override_settings(
    AWS_ACCESS_KEY_ID='fake_access_key',
    AWS_SECRET_ACCESS_KEY='fake_secret_key',
    AWS_STORAGE_BUCKET_NAME='test-bucket',
    AWS_DEFAULT_ACL=None,
    AWS_S3_REGION_NAME='us-east-1',
)
class S3IntegrationTestCase(TestCase):
    

    def setUp(self):
        # 1) Create the 'fake' bucket in the mocked S3 environment
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.s3_client.create_bucket(Bucket='test-bucket')

    def test_s3_upload(self):

        # 2) Create an instance of S3 storage
        storage = S3Boto3Storage()
        # 3) Create a test file
        test_file = SimpleUploadedFile("hello.txt", b"Hello S3 test!")

        # 4) Save it
        saved_name = storage.save("hello.txt", test_file)
        self.assertEqual(saved_name, "hello.txt")

        # 5) Verify the object is in 'test-bucket'
        response = self.s3_client.list_objects_v2(Bucket="test-bucket")
        keys = [obj['Key'] for obj in response.get('Contents', [])]
        self.assertIn("hello.txt", keys, "hello.txt not found in mock S3")

    def test_s3_upload_subfolder(self):

        storage = S3Boto3Storage()
        test_file = SimpleUploadedFile("test2.txt", b"Subfolder test")

        saved_name = storage.save("attachments/2025/03/03/test2.txt", test_file)
        self.assertEqual(saved_name, "attachments/2025/03/03/test2.txt")

        response = self.s3_client.list_objects_v2(Bucket="test-bucket")
        keys = [obj['Key'] for obj in response.get('Contents', [])]
        self.assertIn("attachments/2025/03/03/test2.txt", keys)
