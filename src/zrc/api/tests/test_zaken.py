import unittest
from datetime import date
from unittest.mock import patch

from django.contrib.gis.geos import Point
from django.test import override_settings, tag
from django.utils import timezone

from dateutil.relativedelta import relativedelta
from rest_framework import status
from rest_framework.test import APITestCase
from vng_api_common.constants import (
    Archiefnominatie,
    BrondatumArchiefprocedureAfleidingswijze,
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduiding,
)
from vng_api_common.tests import (
    JWTAuthMixin,
    get_operation_url,
    get_validation_errors,
    reverse,
)
from zds_client.tests.mocks import mock_client

from zrc.datamodel.constants import BetalingsIndicatie
from zrc.datamodel.models import (
    Medewerker,
    NatuurlijkPersoon,
    OrganisatorischeEenheid,
    Zaak,
)
from zrc.datamodel.tests.factories import (
    RolFactory,
    StatusFactory,
    ZaakBesluitFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
)
from zrc.tests.constants import POLYGON_AMSTERDAM_CENTRUM
from zrc.tests.utils import (
    ZAAK_READ_KWARGS,
    ZAAK_WRITE_KWARGS,
    isodatetime,
    utcdatetime,
)

from ..scopes import (
    SCOPE_STATUSSEN_TOEVOEGEN,
    SCOPE_ZAKEN_ALLES_LEZEN,
    SCOPE_ZAKEN_ALLES_VERWIJDEREN,
    SCOPE_ZAKEN_BIJWERKEN,
    SCOPE_ZAKEN_CREATE,
    SCOPEN_ZAKEN_HEROPENEN,
)

# ZTC
ZTC_ROOT = "https://example.com/ztc/api/v1"
CATALOGUS = f"{ZTC_ROOT}/catalogus/878a3318-5950-4642-8715-189745f91b04"
ZAAKTYPE = f"{CATALOGUS}/zaaktypen/283ffaf5-8470-457b-8064-90e5728f413f"
ZAAKTYPE2 = f"{CATALOGUS}/zaaktypen/5dc4ebb0-67c5-4d24-9666-a11f169a6e8c"
RESULTAATTYPE = f"{ZAAKTYPE}/resultaattypen/5b348dbf-9301-410b-be9e-83723e288785"
STATUSTYPE = f"{ZAAKTYPE}/statustypen/5b348dbf-9301-410b-be9e-83723e288785"
STATUSTYPE2 = f"{ZAAKTYPE}/statustypen/b86aa339-151e-45f0-ad6c-20698f50b6cd"

BESLUIT = "https://example.com/brc/api/v1/besluiten/12345678"
RESPONSES = {
    STATUSTYPE: {
        "url": STATUSTYPE,
        "zaaktype": ZAAKTYPE,
        "volgnummer": 1,
        "isEindstatus": False,
    },
    STATUSTYPE2: {
        "url": STATUSTYPE2,
        "zaaktype": ZAAKTYPE,
        "volgnummer": 2,
        "isEindstatus": True,
    },
}


@override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
class ApiStrategyTests(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_ALLES_LEZEN]
    zaaktype = "https://example.com/foo/bar"

    @unittest.expectedFailure
    def test_api_10_lazy_eager_loading(self):
        raise NotImplementedError

    @unittest.expectedFailure
    def test_api_11_expand_nested_resources(self):
        raise NotImplementedError

    @unittest.expectedFailure
    def test_api_12_subset_fields(self):
        raise NotImplementedError

    def test_api_44_crs_headers(self):
        # We wijken bewust af - EPSG:4326 is de standaard projectie voor WGS84
        # De andere opties in de API strategie lijken in de praktijk niet/nauwelijks
        # gebruikt te worden, en zien er vreemd uit t.o.v. wel courant gebruikte
        # opties.
        zaak = ZaakFactory.create(zaakgeometrie=Point(4.887990, 52.377595))  # LONG LAT
        url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_412_PRECONDITION_FAILED)

        response = self.client.get(url, HTTP_ACCEPT_CRS="dummy")
        self.assertEqual(response.status_code, status.HTTP_406_NOT_ACCEPTABLE)

        response = self.client.get(url, HTTP_ACCEPT_CRS="EPSG:4326")
        self.assertEqual(response["Content-Crs"], "EPSG:4326")

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_api_51_status_codes(self, *mocks):
        with self.subTest(crud="create"):
            url = reverse("zaak-list")

            response = self.client.post(
                url,
                {
                    "zaaktype": "https://example.com/foo/bar",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-06-11",
                    "startdatum": "2018-06-11",
                },
                **ZAAK_WRITE_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response["Location"], response.data["url"])

        with self.subTest(crud="read"):
            response_detail = self.client.get(response.data["url"], **ZAAK_READ_KWARGS)
            self.assertEqual(response_detail.status_code, status.HTTP_200_OK)


@override_settings(
    LINK_FETCHER="vng_api_common.mocks.link_fetcher_200",
    ZDS_CLIENT_CLASS="vng_api_common.mocks.MockClient",
)
class ZakenAfsluitenTests(JWTAuthMixin, APITestCase):

    scopes = [
        SCOPE_ZAKEN_CREATE,
        SCOPE_ZAKEN_BIJWERKEN,
        SCOPE_ZAKEN_ALLES_LEZEN,
        SCOPE_STATUSSEN_TOEVOEGEN,
    ]
    zaaktype = ZAAKTYPE

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_zaak_afsluiten(self, *mocks):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})

        responses = {
            RESULTAATTYPE: {
                "url": RESULTAATTYPE,
                "zaaktype": ZAAKTYPE,
                "archiefactietermijn": "P10Y",
                "archiefnominatie": Archiefnominatie.blijvend_bewaren,
                "brondatumArchiefprocedure": {
                    "afleidingswijze": BrondatumArchiefprocedureAfleidingswijze.afgehandeld,
                    "datumkenmerk": None,
                    "objecttype": None,
                    "procestermijn": None,
                },
            },
            STATUSTYPE: {
                "url": STATUSTYPE,
                "zaaktype": ZAAKTYPE,
                "volgnummer": 1,
                "isEindstatus": False,
            },
            STATUSTYPE2: {
                "url": STATUSTYPE2,
                "zaaktype": ZAAKTYPE,
                "volgnummer": 2,
                "isEindstatus": True,
            },
        }

        # Set initial status
        status_list_url = reverse("status-list")
        with mock_client(responses):
            response = self.client.post(
                status_list_url,
                {
                    "zaak": zaak_url,
                    "statustype": STATUSTYPE,
                    "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
                },
            )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertIsNone(zaak.einddatum)

        # add a result for the case
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {"zaak": zaak_url, "resultaattype": RESULTAATTYPE, "toelichting": ""}

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Set eindstatus
        datum_status_gezet = utcdatetime(2018, 10, 22, 10, 00, 00)

        with mock_client(responses):
            response = self.client.post(
                status_list_url,
                {
                    "zaak": zaak_url,
                    "statustype": STATUSTYPE2,
                    "datumStatusGezet": datum_status_gezet.isoformat(),
                },
            )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertEqual(zaak.einddatum, datum_status_gezet.date())
        self.assertEqual(
            zaak.archiefactiedatum, zaak.einddatum + relativedelta(years=10)
        )


@override_settings(
    LINK_FETCHER="vng_api_common.mocks.link_fetcher_200",
    ZDS_CLIENT_CLASS="vng_api_common.mocks.MockClient",
)
class ZakenTests(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE, SCOPE_ZAKEN_BIJWERKEN, SCOPE_ZAKEN_ALLES_LEZEN]
    zaaktype = ZAAKTYPE

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_enkel_initiele_status_met_scope_aanmaken(self, *mocks):
        """
        Met de scope zaken.aanmaken mag je enkel een status aanmaken als er
        nog geen status was.
        """
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})
        status_list_url = reverse("status-list")

        # initiele status
        with mock_client(RESPONSES):
            response = self.client.post(
                status_list_url,
                {
                    "zaak": zaak_url,
                    "statustype": STATUSTYPE,
                    "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
                },
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # extra status - mag niet, onafhankelijk van de data
        with mock_client(RESPONSES):
            response = self.client.post(
                status_list_url,
                {
                    "zaak": zaak_url,
                    "statustype": STATUSTYPE,
                    "datumStatusGezet": isodatetime(2018, 10, 2, 10, 00, 00),
                },
            )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(zaak.status_set.count(), 1)

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_zaak_heropen_reset_einddatum(self, *mocks):
        self.autorisatie.scopes = self.autorisatie.scopes + [SCOPEN_ZAKEN_HEROPENEN]
        self.autorisatie.save()

        zaak = ZaakFactory.create(einddatum="2019-01-07", zaaktype=ZAAKTYPE)
        StatusFactory.create(
            zaak=zaak,
            statustype=STATUSTYPE2,
            datum_status_gezet="2019-01-07T12:51:41+0000",
        )
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})
        status_list_url = reverse("status-list")

        # Set status other than eindstatus
        datum_status_gezet = utcdatetime(2019, 1, 7, 12, 53, 25)
        with mock_client(RESPONSES):
            response = self.client.post(
                status_list_url,
                {
                    "zaak": zaak_url,
                    "statustype": STATUSTYPE,
                    "datumStatusGezet": datum_status_gezet.isoformat(),
                },
            )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertIsNone(zaak.einddatum)

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_zaak_met_producten(self, *mocks):
        url = reverse("zaak-list")

        responses = {
            ZAAKTYPE: {
                "url": ZAAKTYPE,
                "productenOfDiensten": [
                    "https://example.com/product/123",
                    "https://example.com/dienst/123",
                ],
            }
        }

        with mock_client(responses):
            response = self.client.post(
                url,
                {
                    "zaaktype": ZAAKTYPE,
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "productenOfDiensten": ["https://example.com/product/123"],
                },
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        zaak = Zaak.objects.get()
        self.assertEqual(len(zaak.producten_of_diensten), 1)

        # update
        with mock_client(responses):
            response2 = self.client.patch(
                response.data["url"],
                {
                    "productenOfDiensten": [
                        "https://example.com/product/123",
                        "https://example.com/dienst/123",
                    ]
                },
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        zaak.refresh_from_db()
        self.assertEqual(len(zaak.producten_of_diensten), 2)

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    @tag("mock_client")
    def test_zaak_vertrouwelijkheidaanduiding_afgeleid(self, *mocks):
        """
        Assert that the default vertrouwelijkheidaanduiding is set.
        """
        url = reverse("zaak-list")
        responses = {
            ZAAKTYPE: {
                "url": ZAAKTYPE,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
            }
        }

        with mock_client(responses):
            response = self.client.post(
                url,
                {
                    "zaaktype": ZAAKTYPE,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                },
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
        )

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    @tag("mock_client")
    def test_zaak_vertrouwelijkheidaanduiding_expliciet(self, *mocks):
        """
        Assert that the default vertrouwelijkheidaanduiding is set.
        """
        url = reverse("zaak-list")
        responses = {
            ZAAKTYPE: {
                "url": ZAAKTYPE,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.zaakvertrouwelijk,
            }
        }

        with mock_client(responses):
            response = self.client.post(
                url,
                {
                    "zaaktype": ZAAKTYPE,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-12-24",
                    "startdatum": "2018-12-24",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                },
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["vertrouwelijkheidaanduiding"],
            VertrouwelijkheidsAanduiding.openbaar,
        )

    def test_deelzaken(self):
        hoofdzaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        deelzaak = ZaakFactory.create(hoofdzaak=hoofdzaak, zaaktype=ZAAKTYPE)
        detail_url = reverse(hoofdzaak)
        deelzaak_url = reverse(deelzaak)

        response = self.client.get(detail_url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["deelzaken"], [f"http://testserver{deelzaak_url}"]
        )

    def test_zaak_betalingsindicatie_nvt(self):
        zaak = ZaakFactory.create(
            betalingsindicatie=BetalingsIndicatie.gedeeltelijk,
            laatste_betaaldatum=timezone.now(),
            zaaktype=ZAAKTYPE,
        )
        url = reverse(zaak)

        response = self.client.patch(
            url, {"betalingsindicatie": BetalingsIndicatie.nvt}, **ZAAK_WRITE_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["laatsteBetaaldatum"], None)
        zaak.refresh_from_db()
        self.assertIsNone(zaak.laatste_betaaldatum)

    def test_pagination_default(self):
        ZaakFactory.create_batch(2, zaaktype=ZAAKTYPE)
        url = reverse(Zaak)

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    def test_pagination_page_param(self):
        ZaakFactory.create_batch(2, zaaktype=ZAAKTYPE)
        url = reverse(Zaak)

        response = self.client.get(url, {"page": 1}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data["count"], 2)
        self.assertIsNone(response_data["previous"])
        self.assertIsNone(response_data["next"])

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_complex_geometry(self, *mocks):
        url = reverse("zaak-list")

        response = self.client.post(
            url,
            {
                "zaaktype": ZAAKTYPE,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                "bronorganisatie": "517439943",
                "verantwoordelijkeOrganisatie": "517439943",
                "registratiedatum": "2018-12-24",
                "startdatum": "2018-12-24",
                "zaakgeometrie": {
                    "type": "Polygon",
                    "coordinates": [POLYGON_AMSTERDAM_CENTRUM],
                },
            },
            **ZAAK_WRITE_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.json()["zaakgeometrie"])
        zaak = Zaak.objects.get()
        self.assertIsNotNone(zaak.zaakgeometrie)

    def test_filter_startdatum(self):
        ZaakFactory.create(zaaktype=ZAAKTYPE, startdatum="2019-01-01")
        ZaakFactory.create(zaaktype=ZAAKTYPE, startdatum="2019-03-01")
        url = reverse("zaak-list")

        response_gt = self.client.get(
            url, {"startdatum__gt": "2019-02-01"}, **ZAAK_READ_KWARGS
        )
        response_lt = self.client.get(
            url, {"startdatum__lt": "2019-02-01"}, **ZAAK_READ_KWARGS
        )
        response_gte = self.client.get(
            url, {"startdatum__gte": "2019-03-01"}, **ZAAK_READ_KWARGS
        )
        response_lte = self.client.get(
            url, {"startdatum__lte": "2019-01-01"}, **ZAAK_READ_KWARGS
        )

        for response in [response_gt, response_lt, response_gte, response_lte]:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)

        self.assertEqual(response_gt.data["results"][0]["startdatum"], "2019-03-01")
        self.assertEqual(response_lt.data["results"][0]["startdatum"], "2019-01-01")
        self.assertEqual(response_gte.data["results"][0]["startdatum"], "2019-03-01")
        self.assertEqual(response_lte.data["results"][0]["startdatum"], "2019-01-01")

    def test_sort_startdatum(self):
        ZaakFactory.create(zaaktype=ZAAKTYPE, startdatum="2019-01-01")
        ZaakFactory.create(zaaktype=ZAAKTYPE, startdatum="2019-03-01")
        ZaakFactory.create(zaaktype=ZAAKTYPE, startdatum="2019-02-01")
        url = reverse("zaak-list")

        response = self.client.get(url, {"ordering": "-startdatum"}, **ZAAK_READ_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data["results"]

        self.assertEqual(data[0]["startdatum"], "2019-03-01")
        self.assertEqual(data[1]["startdatum"], "2019-02-01")
        self.assertEqual(data[2]["startdatum"], "2019-01-01")

    def test_zaak_eigenschappen_as_inline(self):
        zaak1 = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak2 = ZaakFactory.create(zaaktype=ZAAKTYPE)
        eigenschap1, eigenschap2 = ZaakEigenschapFactory.create_batch(2, zaak=zaak1)

        url = reverse(Zaak)

        response = self.client.get(url, **ZAAK_READ_KWARGS)

        results = response.data["results"]
        self.assertEqual(results[0]["eigenschappen"], [])

        eigenschap1_url = reverse(
            "zaakeigenschap-detail",
            kwargs={"version": 1, "zaak_uuid": zaak1.uuid, "uuid": eigenschap1.uuid},
        )
        eigenschap2_url = reverse(
            "zaakeigenschap-detail",
            kwargs={"version": 1, "zaak_uuid": zaak1.uuid, "uuid": eigenschap2.uuid},
        )

        eigenschappen = results[1]["eigenschappen"]
        self.assertIn(f"http://testserver{eigenschap1_url}", eigenschappen)
        self.assertIn(f"http://testserver{eigenschap2_url}", eigenschappen)

    def test_filter_max_vertrouwelijkheidaanduiding(self):
        zaak1 = ZaakFactory.create(
            zaaktype=ZAAKTYPE,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.openbaar,
        )
        zaak2 = ZaakFactory.create(
            zaaktype=ZAAKTYPE,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduiding.geheim,
        )

        url = reverse(Zaak)

        response = self.client.get(
            url,
            {
                "maximaleVertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.zaakvertrouwelijk
            },
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["url"],
            f"http://testserver{reverse(zaak1)}",
        )
        self.assertNotEqual(
            response.data["results"][0]["url"],
            f"http://testserver{reverse(zaak2)}",
        )

    def test_filter_rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn_max_length(
        self,
    ):
        ZaakFactory.create(zaaktype=ZAAKTYPE, startdatum="2019-01-01")
        ZaakFactory.create(zaaktype=ZAAKTYPE, startdatum="2019-03-01")
        url = reverse("zaak-list")

        response = self.client.get(
            url,
            {"rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": "0" * 10},
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(
            response, "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn"
        )
        self.assertEqual(error["code"], "max_length")

    def test_filter_rol__betrokkeneIdentificatie__medewerker__identificatie_max_length(
        self,
    ):
        ZaakFactory.create(zaaktype=ZAAKTYPE, startdatum="2019-01-01")
        ZaakFactory.create(zaaktype=ZAAKTYPE, startdatum="2019-03-01")
        url = reverse("zaak-list")

        response = self.client.get(
            url,
            {"rol__betrokkeneIdentificatie__medewerker__identificatie": "0" * 25},
            **ZAAK_READ_KWARGS,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(
            response, "rol__betrokkeneIdentificatie__medewerker__identificatie"
        )
        self.assertEqual(error["code"], "max_length")


@override_settings(
    LINK_FETCHER="vng_api_common.mocks.link_fetcher_200",
    ZDS_CLIENT_CLASS="vng_api_common.mocks.MockClient",
)
class HoofdZaakTests(JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    @tag("mock_client")
    def test_create_deelzaak_missing_deelzaaktype_relation(self, *mocks):
        hoofdzaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        detail_url = reverse(hoofdzaak)

        responses = {
            ZAAKTYPE: {"url": ZAAKTYPE, "deelzaaktypen": []},
        }

        with mock_client(responses):

            response = self.client.post(
                reverse(Zaak),
                {
                    "zaaktype": ZAAKTYPE2,
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "hoofdzaak": detail_url,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-06-11",
                    "startdatum": "2018-06-11",
                },
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "invalid-deelzaaktype")

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    @tag("mock_client")
    def test_create_deelzaak_success(self, *mocks):
        hoofdzaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        detail_url = reverse(hoofdzaak)

        responses = {
            ZAAKTYPE: {"url": ZAAKTYPE, "deelzaaktypen": [ZAAKTYPE2]},
        }

        with mock_client(responses):

            response = self.client.post(
                reverse(Zaak),
                {
                    "zaaktype": ZAAKTYPE2,
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduiding.openbaar,
                    "hoofdzaak": detail_url,
                    "bronorganisatie": "517439943",
                    "verantwoordelijkeOrganisatie": "517439943",
                    "registratiedatum": "2018-06-11",
                    "startdatum": "2018-06-11",
                },
                **ZAAK_WRITE_KWARGS,
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Zaak.objects.count(), 2)


class ZakenDeleteTests(JWTAuthMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_ALLES_VERWIJDEREN]
    zaaktype = ZAAKTYPE

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_delete_zaak(self, *mocks):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})

        response = self.client.delete(zaak_url, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Zaak.objects.exists())

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    def test_delete_zaak_with_related_besluit(self, *mocks):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaakbesluit = ZaakBesluitFactory.create(zaak=zaak, besluit=BESLUIT)
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})

        response = self.client.delete(zaak_url, **ZAAK_WRITE_KWARGS)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error = get_validation_errors(response, "nonFieldErrors")
        self.assertEqual(error["code"], "related-besluiten")


class ZaakArchivingTests(JWTAuthMixin, APITestCase):

    heeft_alle_autorisaties = True

    @patch("vng_api_common.validators.fetcher")
    @patch("vng_api_common.validators.obj_has_shape", return_value=True)
    @override_settings(LINK_FETCHER="vng_api_common.mocks.link_fetcher_200")
    def test_zaak_archiefactiedatum_afleidingswijze_ingangsdatum_besluit(self, *mocks):
        zaak = ZaakFactory.create(zaaktype=ZAAKTYPE)
        zaak_url = reverse("zaak-detail", kwargs={"uuid": zaak.uuid})

        responses = {
            RESULTAATTYPE: {
                "url": RESULTAATTYPE,
                "zaaktype": ZAAKTYPE,
                "archiefactietermijn": "P10Y",
                "archiefnominatie": Archiefnominatie.blijvend_bewaren,
                "brondatumArchiefprocedure": {
                    "afleidingswijze": BrondatumArchiefprocedureAfleidingswijze.ingangsdatum_besluit,
                    "datumkenmerk": None,
                    "objecttype": None,
                    "procestermijn": None,
                },
            },
            STATUSTYPE: {
                "url": STATUSTYPE,
                "zaaktype": ZAAKTYPE,
                "volgnummer": 1,
                "isEindstatus": False,
            },
            STATUSTYPE2: {
                "url": STATUSTYPE2,
                "zaaktype": ZAAKTYPE,
                "volgnummer": 2,
                "isEindstatus": True,
            },
            BESLUIT: {"url": BESLUIT, "ingangsdatum": "2020-05-03"},
        }

        ZaakBesluitFactory.create(zaak=zaak, besluit=BESLUIT)

        # Set initial status
        status_list_url = reverse("status-list")
        with mock_client(responses):
            response = self.client.post(
                status_list_url,
                {
                    "zaak": zaak_url,
                    "statustype": STATUSTYPE,
                    "datumStatusGezet": isodatetime(2018, 10, 1, 10, 00, 00),
                },
            )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertIsNone(zaak.einddatum)

        # add a result for the case
        resultaat_create_url = get_operation_url("resultaat_create")
        data = {"zaak": zaak_url, "resultaattype": RESULTAATTYPE, "toelichting": ""}

        with mock_client(responses):
            response = self.client.post(resultaat_create_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        # Set eindstatus
        datum_status_gezet = utcdatetime(2018, 10, 22, 10, 00, 00)

        with mock_client(responses):
            response = self.client.post(
                status_list_url,
                {
                    "zaak": zaak_url,
                    "statustype": STATUSTYPE2,
                    "datumStatusGezet": datum_status_gezet.isoformat(),
                },
            )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        zaak.refresh_from_db()
        self.assertEqual(zaak.einddatum, datum_status_gezet.date())
        self.assertEqual(
            zaak.archiefactiedatum, date(2030, 5, 3)  # 2020-05-03 + 10 years
        )


class ZakenWerkVoorraadTests(JWTAuthMixin, APITestCase):
    """
    Test that the queries to build up a 'werkvoorraad' work as expected.
    """

    heeft_alle_autorisaties = True

    def test_rol_medewerker_url(self):
        """
        Test that zaken for a specific medewerker can be retrieved.
        """
        url = reverse(Zaak)
        MEDEWERKER = "https://medewerkers.nl/api/v1/medewerkers/1"
        rol1 = RolFactory.create(
            betrokkene=MEDEWERKER,
            betrokkene_type=RolTypes.medewerker,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        rol2 = RolFactory.create(
            betrokkene_type=RolTypes.medewerker,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        RolFactory.create(
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving_generiek=RolOmschrijving.initiator,
        )
        zaak1, zaak2 = rol1.zaak, rol2.zaak

        with self.subTest(filter_on="betrokkeneType"):
            query = {"rol__betrokkeneType": RolTypes.medewerker}

            response = self.client.get(url, query, **ZAAK_READ_KWARGS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 2)
            urls = {result["url"] for result in response.data["results"]}
            self.assertEqual(
                urls,
                {
                    f"http://testserver{reverse(zaak1)}",
                    f"http://testserver{reverse(zaak2)}",
                },
            )

        with self.subTest(filter_on="omschrijving generiek"):
            query = {"rol__omschrijvingGeneriek": RolOmschrijving.behandelaar}

            response = self.client.get(url, query, **ZAAK_READ_KWARGS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 2)
            urls = {result["url"] for result in response.data["results"]}
            self.assertEqual(
                urls,
                {
                    f"http://testserver{reverse(zaak1)}",
                    f"http://testserver{reverse(zaak2)}",
                },
            )

        with self.subTest(filter_on="betrokkene"):
            query = {"rol__betrokkene": MEDEWERKER}

            response = self.client.get(url, query, **ZAAK_READ_KWARGS)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)
            self.assertEqual(
                response.data["results"][0]["url"],
                f"http://testserver{reverse(zaak1)}",
            )

    def test_rol_medewerker_identificatie(self):
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.medewerker,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        Medewerker.objects.create(
            rol=rol,
            identificatie="some-username",
        )

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {"rol__betrokkeneIdentificatie__medewerker__identificatie": "no-match"},
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__medewerker__identificatie": "some-username"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)

    def test_rol_np_bsn(self):
        """
        Essential to be able to fetch all Zaken related to a particular citizen.
        """
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.natuurlijk_persoon,
            omschrijving_generiek=RolOmschrijving.initiator,
        )
        NatuurlijkPersoon.objects.create(
            rol=rol, inp_bsn="129117729"
        )  # http://www.wilmans.com/sofinummer/

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": "000000000"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": "129117729"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)

    def test_rol_organisatorische_eenheid_identificatie(self):
        url = reverse(Zaak)
        rol = RolFactory.create(
            betrokkene_type=RolTypes.organisatorische_eenheid,
            omschrijving_generiek=RolOmschrijving.behandelaar,
        )
        OrganisatorischeEenheid.objects.create(
            rol=rol,
            identificatie="some-id",
        )

        with self.subTest(expected="no-match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__organisatorischeEenheid__identificatie": "no-match"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 0)

        with self.subTest(expected="match"):
            response = self.client.get(
                url,
                {
                    "rol__betrokkeneIdentificatie__organisatorischeEenheid__identificatie": "some-id"
                },
                **ZAAK_READ_KWARGS,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["count"], 1)
