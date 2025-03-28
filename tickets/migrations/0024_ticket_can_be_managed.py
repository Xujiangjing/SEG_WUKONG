# Generated by Django 5.1.6 on 2025-03-20 17:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0023_rename_can_be_managed_ticket_can_be_managed_by_program_officers_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='can_be_managed',
            field=models.BooleanField(default=True, help_text='Whether the ticket can be managed by the current user.'),
        ),
    ]
