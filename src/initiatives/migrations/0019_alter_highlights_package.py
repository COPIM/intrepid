# Generated by Django 3.2.8 on 2023-03-14 12:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0064_order_email_address'),
        ('initiatives', '0018_auto_20230313_2126'),
    ]

    operations = [
        migrations.AlterField(
            model_name='highlights',
            name='package',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='package.basepackage'),
        ),
    ]
