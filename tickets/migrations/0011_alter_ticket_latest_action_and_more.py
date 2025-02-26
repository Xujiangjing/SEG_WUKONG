# Generated by Django 5.1.6 on 2025-02-26 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0010_merge_20250226_1546'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ticket',
            name='latest_action',
            field=models.CharField(blank=True, choices=[('created', 'Created'), ('status_updated', 'Status Updated'), ('priority_updated', 'Priority Updated'), ('redirected', 'Redirected'), ('responded', 'Responded'), ('closed', 'Closed'), ('merged', 'Merged')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='ticketactivity',
            name='action',
            field=models.CharField(choices=[('created', 'Created'), ('status_updated', 'Status Updated'), ('priority_updated', 'Priority Updated'), ('redirected', 'Redirected'), ('responded', 'Responded'), ('closed', 'Closed'), ('merged', 'Merged')], max_length=100),
        ),
    ]
