# Generated by Django 3.2.8 on 2021-11-28 16:22

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('access', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='access_code',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]
