# Generated by Django 3.2.8 on 2023-10-08 16:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('initiatives', '0021_alter_initiative_more_info'),
        ('package', '0065_auto_20230621_1932'),
    ]

    operations = [
        migrations.AlterField(
            model_name='basepackage',
            name='pricing_display',
            field=models.CharField(help_text='Display version of pricing eg. £1000-£2000', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='initiative',
            field=models.ForeignKey(blank=True, help_text='If signup inserted by initiative store here.', null=True, on_delete=django.db.models.deletion.CASCADE, to='initiatives.initiative'),
        ),
    ]
