# Generated by Django 3.2.8 on 2024-11-12 15:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0072_auto_20241112_1518'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='term',
            field=models.IntegerField(default=1),
        ),
    ]
