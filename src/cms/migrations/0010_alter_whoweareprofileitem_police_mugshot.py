# Generated by Django 3.2.8 on 2022-04-15 19:32

import accounts.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0009_whoweareprofileitem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='whoweareprofileitem',
            name='police_mugshot',
            field=models.ImageField(blank=True, null=True, upload_to=accounts.models.profile_images_upload_path, verbose_name='Profile image'),
        ),
    ]
