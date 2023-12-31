# Generated by Django 3.2.8 on 2021-12-05 18:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vocab', '0006_alter_bandingvocab_text'),
    ]

    operations = [
        migrations.CreateModel(
            name='StandardVocab',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('standard_name', models.CharField(max_length=255)),
                ('text', models.TextField(blank=True, help_text='The text of the attested standard.', max_length=255, null=True)),
            ],
        ),
    ]
