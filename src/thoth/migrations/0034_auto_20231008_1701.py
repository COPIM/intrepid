# Generated by Django 3.2.8 on 2023-10-08 17:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thoth', '0033_auto_20231008_1659'),
    ]

    operations = [
        migrations.AlterField(
            model_name='work',
            name='cover_url',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='work',
            name='landing_page',
            field=models.TextField(blank=True, default=None, null=True),
        ),
    ]
