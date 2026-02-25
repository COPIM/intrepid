from django.db import migrations


def add_basket_message_site_texts(apps, schema_editor):
    SiteText = apps.get_model('cms', 'SiteText')
    SiteText.objects.get_or_create(
        key='package_already_in_quote',
        defaults={
            'body': 'The package you selected has already been added to this quote.',
            'body_en': 'The package you selected has already been added to this quote.',
            'help_text': 'Message shown when a user tries to add a package that is already in their basket.',
        }
    )
    SiteText.objects.get_or_create(
        key='package_added_to_basket',
        defaults={
            'body': '{} added to basket.',
            'body_en': '{} added to basket.',
            'help_text': 'Message shown when a package is successfully added to the basket. {} is replaced with the package name.',
        }
    )
    SiteText.objects.get_or_create(
        key='from',
        defaults={
            'body': 'From',
            'body_en': 'From',
            'help_text': 'Pricing range display: "From X to Y (in Z)"',
        }
    )
    SiteText.objects.get_or_create(
        key='around',
        defaults={
            'body': 'Around',
            'body_en': 'Around',
            'help_text': 'Pricing display when all prices are the same: "Around X"',
        }
    )


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0043_auto_20251202_1250'),
    ]

    operations = [
        migrations.RunPython(add_basket_message_site_texts),
    ]
