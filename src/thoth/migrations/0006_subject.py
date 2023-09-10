# Generated by Django 3.2.4 on 2021-08-15 16:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('thoth', '0005_auto_20210815_1602'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('thoth_id', models.UUIDField()),
                ('thoth_instance', models.URLField(default='https://api.thoth.pub')),
                ('subject_type', models.CharField(max_length=255)),
                ('subject_ordinal', models.IntegerField(blank=True)),
                ('subject_code', models.CharField(max_length=255)),
                ('work', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='thoth.work')),
            ],
        ),
    ]
