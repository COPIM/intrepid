# Generated by Django 3.2.4 on 2021-08-21 10:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('initiatives', '0003_alter_initiative_users'),
    ]

    operations = [
        migrations.AddField(
            model_name='initiative',
            name='active',
            field=models.BooleanField(default=False),
        ),
    ]
