# Generated by Django 3.2.8 on 2022-05-08 14:06

import accounts.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0022_alter_version_pull_quote'),
    ]

    operations = [
        migrations.AddField(
            model_name='pageupdate',
            name='mid_page_image',
            field=models.ImageField(blank=True, default=None, null=True, upload_to=accounts.models.profile_images_upload_path, verbose_name='Mid-Page Banner Image (1250x500)'),
        ),
        migrations.AlterField(
            model_name='pageupdate',
            name='thumbnail_image',
            field=models.ImageField(blank=True, null=True, upload_to=accounts.models.profile_images_upload_path, verbose_name='Page Thumbnail (510x302)'),
        ),
    ]
