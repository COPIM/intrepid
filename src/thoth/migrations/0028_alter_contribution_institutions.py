# Generated by Django 3.2.8 on 2021-12-02 10:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('thoth', '0027_auto_20211202_0941'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contribution',
            name='institutions',
            field=models.ManyToManyField(blank=True, to='thoth.Institution'),
        ),
    ]
