# Generated by Django 3.2.8 on 2023-03-13 21:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0064_order_email_address'),
        ('initiatives', '0017_alter_highlights_body'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='highlights',
            name='initiative',
        ),
        migrations.AddField(
            model_name='highlights',
            name='package',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='package.package'),
            preserve_default=False,
        ),
    ]
