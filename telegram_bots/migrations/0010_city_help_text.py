# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-08-31 18:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bots', '0009_auto_20170812_2102'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='help_text',
            field=models.CharField(default='', max_length=8192),
            preserve_default=False,
        ),
    ]