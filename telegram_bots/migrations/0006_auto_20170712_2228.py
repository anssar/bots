# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-07-12 22:28
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('telegram_bots', '0005_auto_20170706_2104'),
    ]

    operations = [
        migrations.CreateModel(
            name='CityGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
            ],
        ),
        migrations.AddField(
            model_name='city',
            name='show_on_register',
            field=models.BooleanField(default=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='city',
            name='city_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='telegram_bots.CityGroup'),
        ),
    ]
