# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-09-09 18:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bots', '0011_orderhistory'),
    ]

    operations = [
        migrations.CreateModel(
            name='JuridicalClientGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_group_id', models.IntegerField()),
            ],
        ),
    ]
