# Generated by Django 3.2.4 on 2021-08-15 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vocab', '0003_bandingvocab_text'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bandingvocab',
            name='lower_limit',
            field=models.IntegerField(blank=True, help_text='Lower limit of banding size eg 1000', null=True),
        ),
        migrations.AlterField(
            model_name='bandingvocab',
            name='text',
            field=models.TextField(blank=True, help_text='For non-fte banding types add the tex there.', null=True),
        ),
    ]
