# Generated manually to add user_report_number field

from django.db import migrations, models


def populate_user_report_numbers(apps, schema_editor):
    """Populate user_report_number for existing reports"""
    Report = apps.get_model('api', 'Report')
    
    # Group reports by user and assign sequential numbers
    users_reports = {}
    for report in Report.objects.all().order_by('owner_id', 'created_at'):
        if report.owner_id not in users_reports:
            users_reports[report.owner_id] = 1
        else:
            users_reports[report.owner_id] += 1
        
        report.user_report_number = users_reports[report.owner_id]
        report.save(update_fields=['user_report_number'])


def reverse_populate_user_report_numbers(apps, schema_editor):
    """Reverse migration - nothing to do since we're removing the field"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_vsme_register'),
    ]

    operations = [
        migrations.AddField(
            model_name='report',
            name='user_report_number',
            field=models.PositiveIntegerField(default=1, help_text='Sequential report number per user'),
        ),
        migrations.RunPython(
            populate_user_report_numbers,
            reverse_populate_user_report_numbers,
        ),
    ]
