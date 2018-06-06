# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-07-02 21:35
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bots', '0003_city'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='taxifishkaclient',
            name='from_address',
        ),
        migrations.RemoveField(
            model_name='taxifishkaclient',
            name='registered',
        ),
        migrations.AlterField(
            model_name='taxifishkaclient',
            name='city',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='telegram_bots.City'),
        ),
        migrations.AlterField(
            model_name='taxifishkaclient',
            name='info',
            field=models.CharField(blank=True, max_length=16384, null=True),
        ),
    ]
