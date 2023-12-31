# Generated by Django 3.2.4 on 2021-08-15 16:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('thoth', '0004_alter_contributor_orcid'),
    ]

    operations = [
        migrations.CreateModel(
            name='Publisher',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('publisher_name', models.TextField(blank=True, null=True)),
                ('thoth_id', models.UUIDField()),
                ('thoth_instance', models.URLField(default='https://api.thoth.pub')),
            ],
        ),
        migrations.AddField(
            model_name='contribution',
            name='thoth_instance',
            field=models.URLField(default='https://api.thoth.pub'),
        ),
        migrations.AddField(
            model_name='contributor',
            name='thoth_instance',
            field=models.URLField(default='https://api.thoth.pub'),
        ),
        migrations.AddField(
            model_name='work',
            name='thoth_instance',
            field=models.URLField(default='https://api.thoth.pub'),
        ),
        migrations.AddField(
            model_name='work',
            name='publisher',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='thoth.publisher'),
        ),
    ]
