# Generated by Django 3.2.4 on 2021-08-15 12:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('thoth', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='work',
            old_name='fullTitle',
            new_name='full_title',
        ),
    ]
