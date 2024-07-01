# Generated by Django 3.2.8 on 2024-07-01 10:17

import django.core.files.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0069_auto_20240212_1424'),
    ]

    operations = [
        migrations.AlterField(
            model_name='frozenpackagedocument',
            name='final_zip',
            field=models.FileField(blank=True, storage=django.core.files.storage.FileSystemStorage(base_url='/files', location='/home/martin/Documents/Programming/intrepid/src/files'), upload_to='private_documents'),
        ),
        migrations.AlterField(
            model_name='mediafile',
            name='file',
            field=models.FileField(blank=True, storage=django.core.files.storage.FileSystemStorage(base_url='/files', location='/home/martin/Documents/Programming/intrepid/src/files'), upload_to='private_documents'),
        ),
    ]
