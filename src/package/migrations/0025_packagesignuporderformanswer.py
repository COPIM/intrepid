# Generated by Django 3.2.8 on 2021-12-05 16:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0024_auto_20211205_1536'),
    ]

    operations = [
        migrations.CreateModel(
            name='PackageSignupOrderFormAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_form_answer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='package.orderformanswer')),
                ('package_signup', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='package.packagesignup')),
            ],
        ),
    ]
