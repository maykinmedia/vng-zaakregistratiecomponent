# Generated by Django 2.0.6 on 2018-11-29 10:16

from django.db import migrations
import zds_schema.fields


class Migration(migrations.Migration):

    dependencies = [
        ('datamodel', '0036_zaakinformatieobject_uuid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='zaak',
            name='verantwoordelijke_organisatie',
            field=zds_schema.fields.RSINField(help_text='URL naar de Niet-natuurlijk persoon zijnde de organisatie die eindverantwoordelijk is voor de behandeling van de zaak.', max_length=9),
        ),
    ]