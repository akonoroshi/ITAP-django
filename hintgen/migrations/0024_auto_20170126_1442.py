# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2017-01-26 19:42
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hintgen', '0023_auto_20170117_1924'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sourcestate',
            name='hint',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='code_state', to='hintgen.Hint'),
        ),
        migrations.AlterField(
            model_name='sourcestate',
            name='student',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='code_states', to='hintgen.Student'),
        ),
    ]