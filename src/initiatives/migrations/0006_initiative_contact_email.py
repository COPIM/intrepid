# Generated by Django 3.2.8 on 2021-12-09 10:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('initiatives', '0005_alter_initiative_users'),
    ]

    operations = [
        migrations.AddField(
            model_name='initiative',
            name='contact_email',
            field=models.EmailField(help_text='Default contact email address for this initiative.', max_length=254, null=True),
        ),
    ]
