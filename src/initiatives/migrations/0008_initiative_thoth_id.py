# Generated by Django 3.2.8 on 2022-05-08 16:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('initiatives', '0007_initiative_short_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='initiative',
            name='thoth_id',
            field=models.CharField(blank=True, default=None, max_length=36, null=True, verbose_name='Thoth ID (a UUID4 e.g. 9c41b13c-cecc-4f6a-a151-be4682915ef5)'),
        ),
    ]
