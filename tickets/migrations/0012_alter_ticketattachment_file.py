# Generated by Django 5.1.2 on 2025-03-03 02:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0011_alter_ticket_latest_action_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticketattachment',
            name='file',
            field=models.FileField(upload_to='attachments/%Y/%m/%d/'),
        ),
    ]
