from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vocab', '0015_alter_standardvocab_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='bandingvocab',
            name='text_en',
            field=models.CharField(blank=True, help_text='For non-fte banding types add the text here.', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='bandingvocab',
            name='text_de',
            field=models.CharField(blank=True, help_text='For non-fte banding types add the text here.', max_length=255, null=True),
        ),
    ]
