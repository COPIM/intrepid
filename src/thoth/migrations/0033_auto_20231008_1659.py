# Generated by Django 3.2.8 on 2023-10-08 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thoth', '0032_alter_thothsearch_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='work',
            name='cover_url',
            field=models.URLField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name='work',
            name='landing_page',
            field=models.URLField(blank=True, default=None, max_length=512, null=True),
        ),
    ]
