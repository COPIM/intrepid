# Generated by Django 3.2.8 on 2022-06-02 11:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vocab', '0014_auto_20220524_0853'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='standardvocab',
            options={'ordering': ('standard_name',)},
        ),
    ]
