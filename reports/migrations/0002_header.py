# Generated by Django 2.0.4 on 2018-05-18 00:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Header',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inp_head', models.CharField(max_length=250)),
                ('out_head', models.CharField(max_length=250)),
            ],
        ),
    ]
