# Generated by Django 3.2.8 on 2022-05-28 15:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0046_alter_frozenpackagedocument_final_zip'),
    ]

    operations = [
        migrations.AddField(
            model_name='banding',
            name='redirect',
            field=models.URLField(blank=True, default='', null=True),
        ),
    ]
