# Generated by Django 3.2.8 on 2022-05-04 19:36

from django.db import migrations
import django_bleach.models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0021_homepagequote_organization_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='version',
            name='pull_quote',
            field=django_bleach.models.BleachField(blank=True, default='', help_text='The text to display in the pull-quote', null=True),
        ),
    ]
