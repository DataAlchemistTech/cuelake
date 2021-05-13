# Generated by Django 3.2.1 on 2021-05-11 17:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0004_auto_20210509_0239'),
        ('genie', '0010_rename_schedule_customschedule'),
    ]

    operations = [
        migrations.AlterField(
            model_name='runstatus',
            name='worflowRun',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='workflows.workflowrun'),
        ),
    ]
