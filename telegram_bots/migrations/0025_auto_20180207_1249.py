# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-02-07 12:49
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bots', '0024_auto_20180207_1244'),
    ]

    operations = [
        migrations.AlterField(
            model_name='city',
            name='help_text',
            field=models.CharField(blank=True, max_length=8192, null=True),
        ),
    ]
