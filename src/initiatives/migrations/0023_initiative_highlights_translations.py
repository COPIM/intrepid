from django.db import migrations, models
from django_bleach.models import BleachField


class Migration(migrations.Migration):

    dependencies = [
        ('initiatives', '0022_initiative_exclude_from_thoth_filter'),
    ]

    operations = [
        migrations.AddField(
            model_name='initiative',
            name='description_en',
            field=BleachField(
                null=True,
                help_text='Description of the initiative.',
            ),
        ),
        migrations.AddField(
            model_name='initiative',
            name='description_de',
            field=BleachField(
                null=True,
                help_text='Description of the initiative.',
            ),
        ),
        migrations.AddField(
            model_name='initiative',
            name='more_info_en',
            field=BleachField(
                blank=True,
                null=True,
                help_text='Appears on the Initiative/Package more info page.',
            ),
        ),
        migrations.AddField(
            model_name='initiative',
            name='more_info_de',
            field=BleachField(
                blank=True,
                null=True,
                help_text='Appears on the Initiative/Package more info page.',
            ),
        ),
        migrations.AddField(
            model_name='highlights',
            name='title_en',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='highlights',
            name='title_de',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='highlights',
            name='body_en',
            field=BleachField(null=True),
        ),
        migrations.AddField(
            model_name='highlights',
            name='body_de',
            field=BleachField(null=True),
        ),
    ]
