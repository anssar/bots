# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-09-17 20:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bots', '0016_taxifishkaclient_untracked_orders'),
    ]

    operations = [
        migrations.AddField(
            model_name='juridicalclientgroup',
            name='name',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
