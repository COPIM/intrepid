# Generated by Django 3.2.8 on 2021-11-27 15:39

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0011_auto_20211127_1234'),
    ]

    operations = [
        migrations.RenameField(
            model_name='frozenpackagedocument',
            old_name='final_pdf',
            new_name='final_zip',
        ),
        migrations.AddField(
            model_name='frozenpackagedocument',
            name='date_of_freeze',
            field=models.DateField(blank=True, default=datetime.date.today, null=True),
        ),
    ]
