# Generated by Django 3.1.8 on 2021-04-19 13:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0001_initial'),
        ('genie', '0007_auto_20210417_1807'),
    ]

    operations = [
        migrations.AddField(
            model_name='runstatus',
            name='worflowRun',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='workflows.workflowrun'),
        ),
    ]
