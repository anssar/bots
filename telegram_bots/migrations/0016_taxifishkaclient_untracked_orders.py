# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-09-10 01:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bots', '0015_remove_taxifishkaclient_client_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='taxifishkaclient',
            name='untracked_orders',
            field=models.CharField(blank=True, max_length=16384, null=True),
        ),
    ]
