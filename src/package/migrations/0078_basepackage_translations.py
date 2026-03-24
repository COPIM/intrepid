from django.db import migrations, models
from django_bleach.models import BleachField


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0077_auto_20260208_1931'),
    ]

    operations = [
        migrations.AddField(
            model_name='basepackage',
            name='name_en',
            field=models.CharField(help_text='Name of the package', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='basepackage',
            name='name_de',
            field=models.CharField(help_text='Name of the package', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='basepackage',
            name='description_en',
            field=BleachField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='basepackage',
            name='description_de',
            field=BleachField(blank=True, null=True),
        ),
    ]
