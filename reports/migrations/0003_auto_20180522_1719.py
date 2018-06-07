# Generated by Django 2.0.4 on 2018-05-22 22:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_header'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ticker',
            fields=[
                ('inp_ticker', models.CharField(max_length=250, primary_key=True, serialize=False)),
                ('standard_ticker', models.CharField(max_length=30)),
            ],
        ),
        migrations.RemoveField(
            model_name='header',
            name='id',
        ),
        migrations.AlterField(
            model_name='header',
            name='inp_head',
            field=models.CharField(max_length=250, primary_key=True, serialize=False),
        ),
    ]