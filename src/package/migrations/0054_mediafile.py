# Generated by Django 3.2.8 on 2022-06-03 12:15

import django.core.files.storage
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0053_metapackage_contact'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Descriptive name of the file.', max_length=255)),
                ('file', models.FileField(blank=True, storage=django.core.files.storage.FileSystemStorage(base_url='/files', location='/Users/ajrbyers/Code/intrepid/src/files'), upload_to='private_documents')),
                ('date_uploaded', models.DateTimeField(default=django.utils.timezone.now)),
                ('package', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='package.package')),
            ],
        ),
    ]
