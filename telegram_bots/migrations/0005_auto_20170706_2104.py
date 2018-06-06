# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-07-06 21:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bots', '0004_auto_20170702_2135'),
    ]

    operations = [
        migrations.AddField(
            model_name='city',
            name='phone',
            field=models.CharField(default='123123123', max_length=128),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='city',
            name='to_address_check',
            field=models.BooleanField(default=True),
            preserve_default=False,
        ),
    ]
