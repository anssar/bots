# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-10-19 00:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bots', '0019_auto_20171019_0044'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderhistory',
            name='order_id',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
