# Generated by Django 2.0.6 on 2018-06-03 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0006_transaction_matching'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='matching',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
    ]