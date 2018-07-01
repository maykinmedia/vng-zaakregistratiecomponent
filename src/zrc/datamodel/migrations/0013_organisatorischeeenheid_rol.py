# Generated by Django 2.0.6 on 2018-06-13 14:28

from django.db import migrations, models
import django.db.models.deletion
import zds_schema.validators


class Migration(migrations.Migration):

    dependencies = [
        ('datamodel', '0012_zaak_zaakgeometrie'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganisatorischeEenheid',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('organisatie_eenheid_identificatie', models.CharField(help_text='Een korte identificatie van de organisatorische eenheid.', max_length=24, validators=[zds_schema.validators.AlphanumericExcludingDiacritic()])),
                ('organisatie_identificatie', models.PositiveIntegerField(help_text='Het RSIN van de organisatie zijnde een Niet-natuurlijk persoon waarvan de ORGANISATORISCHE EENHEID deel uit maakt.')),
                ('datum_ontstaan', models.DateField(help_text='De datum wrop de organisatorische eenheid is ontstaan.')),
                ('naam', models.CharField(help_text='De feitelijke naam van de organisatorische eenheid.', max_length=50)),
            ],
            options={
                'verbose_name': 'Organisatorische eenheid',
                'verbose_name_plural': 'Organisatorische eenheden',
            },
        ),
        migrations.CreateModel(
            name='Rol',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rolomschrijving', models.CharField(choices=[('Adviseur', 'Adviseur'), ('Behandelaar', 'Behandelaar'), ('Belanghebbende', 'Belanghebbende'), ('Beslisser', 'Beslisser'), ('Initiator', 'Initiator'), ('Klantcontacter', 'Klantcontacter'), ('Zaakcoördinator', 'Zaakcoördinator')], help_text='Algemeen gehanteerde benaming van de aard van de ROL', max_length=80)),
                ('rolomschrijving_generiek', models.CharField(choices=[('Adviseur', 'Adviseur'), ('Behandelaar', 'Behandelaar'), ('Belanghebbende', 'Belanghebbende'), ('Beslisser', 'Beslisser'), ('Initiator', 'Initiator'), ('Klantcontacter', 'Klantcontacter'), ('Zaakcoördinator', 'Zaakcoördinator'), ('Mede-initiator', 'Mede-initiator')], help_text='Algemeen gehanteerde benaming van de aard van de ROL', max_length=40)),
                ('roltoelichting', models.TextField(max_length=1000)),
                ('betrokkene', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='datamodel.OrganisatorischeEenheid')),
                ('zaak', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='datamodel.Zaak')),
            ],
            options={
                'verbose_name': 'Rol',
                'verbose_name_plural': 'Rollen',
            },
        ),
    ]
