# Generated by Django 3.2.8 on 2022-01-27 14:05

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0029_custompackagedocument'),
    ]

    operations = [
        migrations.AlterField(
            model_name='packagesignup',
            name='signup_date',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True),
        ),
    ]
