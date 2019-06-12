# Generated by Django 2.2.2 on 2019-06-12 15:36

import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import vng_api_common.fields


class Migration(migrations.Migration):

    dependencies = [
        ('datamodel', '0060_auto_20190605_0941'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vestiging',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('vestigings_nummer', models.CharField(blank=True, help_text='Een korte unieke aanduiding van de Vestiging.', max_length=24)),
                ('handelsnaam', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(help_text='De naam van de vestiging waaronder gehandeld wordt.', max_length=625), size=None)),
                ('verblijfsadres', models.CharField(blank=True, help_text='De gegevens over het verblijf en adres van de Vestiging', max_length=1000)),
                ('sub_verblijf_buitenland', models.CharField(blank=True, help_text='De gegevens over het verblijf in het buitenland', max_length=1000)),
                ('rol', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='datamodel.Rol')),
            ],
            options={
                'verbose_name': 'vestiging',
            },
        ),
        migrations.CreateModel(
            name='OrganisatorischeEenheid',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identificatie', models.CharField(blank=True, help_text='Een korte identificatie van de organisatorische eenheid.', max_length=24)),
                ('naam', models.CharField(blank=True, help_text='De feitelijke naam van de organisatorische eenheid.', max_length=50)),
                ('is_gehuisvest_in', models.CharField(blank=True, max_length=24)),
                ('rol', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='datamodel.Rol')),
            ],
            options={
                'verbose_name': 'organisatorische eenheid',
            },
        ),
        migrations.CreateModel(
            name='NietNatuurlijkPersoon',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rsin', vng_api_common.fields.RSINField(blank=True, help_text='Het door een kamer toegekend uniek nummer voor de INGESCHREVEN NIET-NATUURLIJK PERSOON', max_length=9)),
                ('nummer_ander_nietnatuurlijk_persoon', models.CharField(help_text='Het door de gemeente uitgegeven uniekenummer voor een ANDER NIET-NATUURLIJK PERSOON', max_length=17)),
                ('statutaire_naam', models.TextField(blank=True, help_text='Naam van de niet-natuurlijke persoon zoals deze is vastgelegd in de statuten (rechtspersoon) of in de vennootschapsovereenkomst is overeengekomen (Vennootschap onder firma of Commanditaire vennootschap).', max_length=500)),
                ('rechtsvorm', models.CharField(blank=True, choices=[('Besloten Vennootschap', 'Besloten Vennootschap'), ('Cooperatie, Europees Economische Samenwerking', 'Cooperatie, Europees Economische Samenwerking'), ('Europese Cooperatieve Venootschap', 'Europese Cooperatieve Venootschap'), ('Europese Naamloze Vennootschap', 'Europese Naamloze Vennootschap'), ('Kerkelijke Organisatie', 'Kerkelijke Organisatie'), ('Naamloze Vennootschap', 'Naamloze Vennootschap'), ('Onderlinge Waarborg Maatschappij', 'Onderlinge Waarborg Maatschappij'), ('Overig privaatrechtelijke rechtspersoon', 'Overig privaatrechtelijke rechtspersoon'), ('Stichting', 'Stichting'), ('Vereniging', 'Vereniging'), ('Vereniging van Eigenaars', 'Vereniging van Eigenaars'), ('Publiekrechtelijke Rechtspersoon', 'Publiekrechtelijke Rechtspersoon'), ('Vennootschap onder Firma', 'Vennootschap onder Firma'), ('Maatschap', 'Maatschap'), ('Rederij', 'Rederij'), ('Commanditaire vennootschap', 'Commanditaire vennootschap'), ('Kapitaalvennootschap binnen EER', 'Kapitaalvennootschap binnen EER'), ('Overige buitenlandse rechtspersoon vennootschap', 'Overige buitenlandse rechtspersoon vennootschap'), ('Kapitaalvennootschap buiten EER', 'Kapitaalvennootschap buiten EER')], help_text='De juridische vorm van de NIET-NATUURLIJK PERSOON.', max_length=30)),
                ('bezoekadres', models.CharField(blank=True, help_text='De gegevens over het adres van de NIET-NATUURLIJK PERSOON', max_length=1000)),
                ('sub_verblijf_buitenland', models.CharField(blank=True, help_text='De gegevens over het verblijf in het buitenland', max_length=1000)),
                ('rol', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='datamodel.Rol')),
            ],
            options={
                'verbose_name': 'niet-natuurlijk persoon',
            },
        ),
        migrations.CreateModel(
            name='NatuurlijkPersoon',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('burgerservicenummer', vng_api_common.fields.BSNField(blank=True, help_text='Het burgerservicenummer, bedoeld in artikel 1.1 van de Wet algemene bepalingen burgerservicenummer.', max_length=9)),
                ('nummer_ander_natuurlijk_persoon', models.CharField(blank=True, help_text='Het door de gemeente uitgegeven unieke nummer voor een ANDER NATUURLIJK PERSOON', max_length=17)),
                ('a_nummer', models.IntegerField(null=True)),
                ('geslachtsnaam', models.CharField(blank=True, help_text='De stam van de geslachtsnaam.', max_length=200)),
                ('voorvoegsel_geslachtsnaam', models.CharField(blank=True, max_length=80)),
                ('voorletters', models.CharField(blank=True, help_text='De verzameling letters die gevormd wordt door de eerste letter van alle in volgorde voorkomende voornamen.', max_length=20)),
                ('voornamen', models.CharField(blank=True, help_text='Voornamen bij de naam die de persoon wenst te voeren.', max_length=200)),
                ('geslachtsaanduiding', models.CharField(blank=True, choices=[('M', 'Man'), ('V', 'Vrouw'), ('O', 'Onbekend')], help_text='Een aanduiding die aangeeft of de persoon een man of een vrouw is, of dat het geslacht nog onbekend is.', max_length=1)),
                ('geboortedatum', models.CharField(blank=True, max_length=18)),
                ('verblijfsadres', models.CharField(blank=True, help_text='De gegevens over het verblijf en adres van de NATUURLIJK PERSOON', max_length=1000)),
                ('sub_verblijf_buitenland', models.CharField(blank=True, help_text='De gegevens over het verblijf in het buitenland', max_length=1000)),
                ('rol', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='datamodel.Rol')),
            ],
            options={
                'verbose_name': 'natuurlijk persoon',
            },
        ),
        migrations.CreateModel(
            name='Medewerker',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identificatie', models.CharField(blank=True, help_text='Een korte unieke aanduiding van de MEDEWERKER.', max_length=24)),
                ('achternaam', models.CharField(blank=True, help_text='De achternaam zoals de MEDEWERKER die in het dagelijkse verkeer gebruikt.', max_length=200)),
                ('voorletters', models.CharField(blank=True, help_text='De verzameling letters die gevormd wordt door de eerste letter van alle in volgorde voorkomende voornamen.', max_length=20)),
                ('voorvoegsel_achternaam', models.CharField(blank=True, help_text='Dat deel van de geslachtsnaam dat voorkomt in Tabel 36 (GBA), voorvoegseltabel, en door een spatie van de geslachtsnaam is', max_length=10)),
                ('rol', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='datamodel.Rol')),
            ],
            options={
                'verbose_name': 'medewerker',
            },
        ),
    ]
