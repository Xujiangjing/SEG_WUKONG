# Generated by Django 5.1.2 on 2025-03-13 23:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0017_dailyticketclosurereport_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mergedticket',
            name='primary_ticket',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='primary_ticket', to='tickets.ticket'),
        ),
    ]
