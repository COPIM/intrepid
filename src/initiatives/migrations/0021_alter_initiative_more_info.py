# Generated by Django 3.2.8 on 2023-10-08 16:59

from django.db import migrations
import django_bleach.models


class Migration(migrations.Migration):

    dependencies = [
        ('initiatives', '0020_alter_highlights_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='initiative',
            name='more_info',
            field=django_bleach.models.BleachField(blank=True, help_text='Appears on the Initiative/Package more info page.', null=True),
        ),
    ]
