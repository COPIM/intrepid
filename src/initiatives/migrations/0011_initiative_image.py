# Generated by Django 3.2.8 on 2022-05-24 09:37

from django.db import migrations, models
import initiatives.models


class Migration(migrations.Migration):

    dependencies = [
        ('initiatives', '0010_initiative_indexed_books'),
    ]

    operations = [
        migrations.AddField(
            model_name='initiative',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=initiatives.models.profile_images_upload_path),
        ),
    ]
