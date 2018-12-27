from unittest.mock import patch

from django.test import override_settings

from rest_framework import status
from rest_framework.test import APITestCase
from zds_schema.tests import JWTScopesMixin, get_validation_errors, reverse
from zds_schema.validators import ResourceValidator, URLValidator

from zrc.datamodel.tests.factories import ZaakFactory

from ..scopes import SCOPE_ZAKEN_ALLES_LEZEN, SCOPE_ZAKEN_CREATE


class ZaakValidationTests(JWTScopesMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE]

    @override_settings(LINK_FETCHER='zds_schema.mocks.link_fetcher_404')
    def test_validate_zaaktype_invalid(self):
        url = reverse('zaak-list')

        response = self.client.post(url, {
            'zaaktype': 'https://example.com/foo/bar',
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': '517439943',
            'registratiedatum': '2018-06-11',
            'startdatum': '2018-06-11',
        }, HTTP_ACCEPT_CRS='EPSG:4326')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, 'zaaktype')
        self.assertEqual(validation_error['code'], URLValidator.code)
        self.assertEqual(validation_error['name'], 'zaaktype')

    @override_settings(LINK_FETCHER='zds_schema.mocks.link_fetcher_200')
    def test_validate_zaaktype_valid(self):
        url = reverse('zaak-list')

        response = self.client.post(url, {
            'zaaktype': 'https://example.com/foo/bar',
            'bronorganisatie': '517439943',
            'verantwoordelijkeOrganisatie': '517439943',
            'registratiedatum': '2018-06-11',
            'startdatum': '2018-06-11',
        }, HTTP_ACCEPT_CRS='EPSG:4326')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_validation_camelcase(self):
        url = reverse('zaak-list')

        response = self.client.post(url, {}, HTTP_ACCEPT_CRS='EPSG:4326')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        bad_casing = get_validation_errors(response, 'verantwoordelijke_organisatie')
        self.assertIsNone(bad_casing)

        good_casing = get_validation_errors(response, 'verantwoordelijkeOrganisatie')
        self.assertIsNotNone(good_casing)

    @patch('zds_schema.validators.fetcher')
    @patch('zds_schema.validators.obj_has_shape', return_value=False)
    @override_settings(LINK_FETCHER='zds_schema.mocks.link_fetcher_200')
    def test_validate_communicatiekanaal_invalid(self, mock_has_shape, mock_fetcher):
        url = reverse('zaak-list')
        body = {'communicatiekanaal': 'https://ref.tst.vng.cloud/referentielijsten/api/v1/'}

        response = self.client.post(url, body, HTTP_ACCEPT_CRS='EPSG:4326')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, 'communicatiekanaal')
        self.assertEqual(error['code'], ResourceValidator.code)

    @patch('zds_schema.validators.fetcher')
    def test_validate_communicatiekanaal_valid(self, mock_fetcher):
        url = reverse('zaak-list')
        body = {'communicatiekanaal': 'https://example.com/dummy'}

        with override_settings(LINK_FETCHER='zds_schema.mocks.link_fetcher_200'):
            with patch('zds_schema.validators.obj_has_shape', return_value=True):
                response = self.client.post(url, body, HTTP_ACCEPT_CRS='EPSG:4326')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = get_validation_errors(response, 'communicatiekanaal')
        self.assertIsNone(error)


class ZaakInformatieObjectValidationTests(JWTScopesMixin, APITestCase):

    scopes = [SCOPE_ZAKEN_CREATE]

    @override_settings(
        LINK_FETCHER='zds_schema.mocks.link_fetcher_404',
        ZDS_CLIENT_CLASS='zds_schema.mocks.ObjectInformatieObjectClient'
    )
    def test_informatieobject_invalid(self):
        zaak = ZaakFactory.create()
        url = reverse('zaakinformatieobject-list', kwargs={'zaak_uuid': zaak.uuid})

        response = self.client.post(url, {'informatieobject': 'https://drc.nl/api/v1'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        validation_error = get_validation_errors(response, 'informatieobject')
        self.assertEqual(validation_error['code'], URLValidator.code)
        self.assertEqual(validation_error['name'], 'informatieobject')


class FilterValidationTests(JWTScopesMixin, APITestCase):
    """
    Test that incorrect filter usage results in HTTP 400.
    """

    scopes = [SCOPE_ZAKEN_ALLES_LEZEN]

    def test_zaak_invalid_filters(self):
        url = reverse('zaak-list')

        invalid_filters = {
            'zaaktype': '123',
            'bronorganisatie': '123',
            'foo': 'bar',
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value}, HTTP_ACCEPT_CRS='EPSG:4326')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rol_invalid_filters(self):
        url = reverse('rol-list')

        invalid_filters = {
            'zaak': '123',  # must be a url
            'betrokkene': '123',  # must be a url
            'betrokkeneType': 'not-a-valid-choice',  # must be a pre-defined choice
            'rolomschrijving': 'not-a-valid-choice',  # must be a pre-defined choice
            'foo': 'bar',
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_status_invalid_filters(self):
        url = reverse('status-list')

        invalid_filters = {
            'zaak': '123',  # must be a url
            'statusType': '123',  # must be a url
            'foo': 'bar',
        }

        for key, value in invalid_filters.items():
            with self.subTest(query_param=key, value=value):
                response = self.client.get(url, {key: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
