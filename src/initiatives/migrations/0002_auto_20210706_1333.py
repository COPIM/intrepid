# Generated by Django 3.2.4 on 2021-07-06 13:33

from django.db import migrations
import django_bleach.models


class Migration(migrations.Migration):

    dependencies = [
        ('initiatives', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='initiative',
            options={'ordering': ('name',)},
        ),
        migrations.AddField(
            model_name='initiative',
            name='description',
            field=django_bleach.models.BleachField(help_text='Description of the initiative.', null=True),
        ),
    ]
