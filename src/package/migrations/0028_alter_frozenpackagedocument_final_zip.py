# Generated by Django 3.2.8 on 2022-03-20 20:06

import django.core.files.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0027_alter_frozenpackagedocument_final_zip'),
    ]

    operations = [
        migrations.AlterField(
            model_name='frozenpackagedocument',
            name='final_zip',
            field=models.FileField(blank=True, storage=django.core.files.storage.FileSystemStorage(base_url='/files', location='/mnt/c/Users/ajrby/code/intrepid/src/files'), upload_to='private_documents'),
        ),
    ]
