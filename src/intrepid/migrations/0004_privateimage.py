# Generated by Django 3.2.8 on 2022-04-19 11:16

import django.core.files.storage
from django.db import migrations, models
import intrepid.models


class Migration(migrations.Migration):

    dependencies = [
        ('intrepid', '0003_auto_20220327_1110'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrivateImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(storage=django.core.files.storage.FileSystemStorage(location='/Users/ajrbyers/Code/intrepid/src'), upload_to=intrepid.models.private_images_upload_path)),
            ],
        ),
    ]
