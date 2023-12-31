# Generated by Django 3.2.8 on 2022-06-01 13:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_alter_profile_activation_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='notify_targeted_updates',
            field=models.BooleanField(default=False, verbose_name='Receive initiative update notifications where your institution is targeted'),
        ),
    ]
