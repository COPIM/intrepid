# Generated by Django 3.2.4 on 2021-10-23 16:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('package', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AggregateAssignmentAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer', models.TextField(blank=True, null=True)),
                ('edited_answer', models.TextField(blank=True, null=True)),
                ('author_can_see', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='AggregateFormElement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('kind', models.CharField(choices=[('text', 'Text Field'), ('textarea', 'Text Area'), ('check', 'Check Box'), ('select', 'Select'), ('email', 'Email'), ('upload', 'Upload'), ('date', 'Date')], max_length=50)),
                ('choices', models.CharField(blank=True, help_text='Separate choices with a |.', max_length=1000, null=True)),
                ('required', models.BooleanField(default=True)),
                ('order', models.IntegerField()),
                ('width', models.CharField(choices=[('large-4 columns', 'third'), ('large-6 columns', 'half'), ('large-12 columns', 'full')], max_length=20)),
                ('help_text', models.TextField(blank=True, null=True)),
            ],
            options={
                'ordering': ('order', 'name'),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='FrozenAggregateFormElement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('kind', models.CharField(choices=[('text', 'Text Field'), ('textarea', 'Text Area'), ('check', 'Check Box'), ('select', 'Select'), ('email', 'Email'), ('upload', 'Upload'), ('date', 'Date')], max_length=50)),
                ('choices', models.CharField(blank=True, help_text='Separate choices with a |.', max_length=1000, null=True)),
                ('required', models.BooleanField(default=True)),
                ('order', models.IntegerField()),
                ('width', models.CharField(choices=[('large-4 columns', 'third'), ('large-6 columns', 'half'), ('large-12 columns', 'full')], max_length=20)),
                ('help_text', models.TextField(blank=True, null=True)),
                ('answer', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='frozen_element', to='package.aggregateassignmentanswer')),
                ('form_element', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='package.aggregateformelement')),
            ],
            options={
                'ordering': ('order', 'name'),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AggregateFormAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer', models.TextField()),
                ('form_element', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='package.aggregateformelement')),
            ],
        ),
        migrations.CreateModel(
            name='AggregateForm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('slug', models.SlugField(max_length=200)),
                ('intro', models.TextField(help_text='Message displayed at the start of the review form.')),
                ('thanks', models.TextField(help_text='Message displayed after the reviewer is finished.')),
                ('deleted', models.BooleanField(default=False)),
                ('elements', models.ManyToManyField(to='package.AggregateFormElement')),
            ],
        ),
        migrations.AddField(
            model_name='aggregateassignmentanswer',
            name='original_element',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='package.aggregateformelement'),
        ),
    ]
