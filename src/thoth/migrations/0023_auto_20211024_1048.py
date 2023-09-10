# Generated by Django 3.2.4 on 2021-10-24 10:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thoth', '0022_rorrecord_country'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rorrecord',
            name='aliases',
        ),
        migrations.AddIndex(
            model_name='rorrecord',
            index=models.Index(fields=['institution_name'], name='thoth_rorre_institu_1464c9_idx'),
        ),
    ]
