from django.db import migrations, models


def unmark_frontend_site_texts(apps, schema_editor):
    SiteText = apps.get_model('cms', 'SiteText')

    frontend_keys = [
        'select_currency',
        'institutions_fte',
        'fte_student_count_prompt',
        'jisc_banding',
        'jisc_banding_info',
        'classification_by_size_income',
        'org_size_country_classification_note',
        'save_button',
        'email_address',
        'contact_name',
        'institution',
        'update'
    ]

    SiteText.objects.filter(key__in=frontend_keys).update(frontend=True)


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0042_auto_20250414_1249'),
    ]

    operations = [
        migrations.RunPython(unmark_frontend_site_texts),
    ]
