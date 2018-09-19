# Generated by Django 2.0.6 on 2018-09-19 10:08

from django.db import migrations
from django.db.models import F
from zds_schema.constants import ObjectTypes


def zaak_naar_object(apps, _):
    ObjectInformatieObject = apps.get_model('datamodel', 'ObjectInformatieObject')
    ObjectInformatieObject.objects.update(
        object=F('zaak'),
        object_type=ObjectTypes.zaak
    )


class Migration(migrations.Migration):

    dependencies = [
        ('datamodel', '0013_auto_20180919_1002'),
    ]

    operations = [
        migrations.RunPython(zaak_naar_object, migrations.RunPython.noop),
    ]
