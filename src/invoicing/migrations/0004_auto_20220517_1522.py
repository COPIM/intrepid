# Generated by Django 3.2.8 on 2022-05-17 15:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoicing', '0003_auto_20220513_1512'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='invoicelog',
            options={'ordering': ('-date_time',)},
        ),
        migrations.AlterField(
            model_name='signupinvoice',
            name='payment_processor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='invoicing.paymentprocessor'),
        ),
    ]
