# Generated by Django 3.2.8 on 2022-05-24 08:53

import django.core.files.storage
from django.db import migrations, models
import intrepid.models


class Migration(migrations.Migration):

    dependencies = [
        ('intrepid', '0016_alter_sitesetup_base_copyright_notice'),
    ]

    operations = [
        migrations.AlterField(
            model_name='privateimage',
            name='image',
            field=models.ImageField(storage=django.core.files.storage.FileSystemStorage(location='/mnt/c/Users/ajrby/code/intrepid/src/files/private_images'), upload_to=intrepid.models.private_images_upload_path),
        ),
    ]
