# Generated by Django 3.2.4 on 2021-10-24 14:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('thoth', '0023_auto_20211024_1048'),
        ('accounts', '0004_accountbandingchoices'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='affiliation',
        ),
        migrations.AddField(
            model_name='profile',
            name='institution',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='thoth.rorrecord'),
        ),
    ]
