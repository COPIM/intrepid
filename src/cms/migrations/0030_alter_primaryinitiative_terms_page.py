# Generated by Django 3.2.8 on 2022-06-26 16:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0029_pageupdate_notification_sent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='primaryinitiative',
            name='terms_page',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='terms', to='cms.pageupdate'),
        ),
    ]
