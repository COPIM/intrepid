# Generated by Django 3.2.8 on 2023-05-11 08:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('initiatives', '0019_alter_highlights_package'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='highlights',
            options={'ordering': ('pk',)},
        ),
    ]
