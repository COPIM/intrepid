# Generated by Django 3.2.4 on 2021-08-29 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0003_auto_20210829_1257'),
    ]

    operations = [
        migrations.AddField(
            model_name='pageupdate',
            name='is_update',
            field=models.BooleanField(default=False),
        ),
    ]
