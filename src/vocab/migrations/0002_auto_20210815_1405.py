# Generated by Django 3.2.4 on 2021-08-15 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vocab', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bandingvocab',
            options={'ordering': ('order',)},
        ),
        migrations.AddField(
            model_name='bandingvocab',
            name='order',
            field=models.PositiveIntegerField(default=99),
        ),
        migrations.AlterField(
            model_name='bandingvocab',
            name='upper_limit',
            field=models.IntegerField(blank=True, help_text='Upper limit of banding size eg 10000.', null=True),
        ),
    ]
