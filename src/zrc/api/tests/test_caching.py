"""
Test that the caching mechanisms are in place.
"""
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from vng_api_common.tests import CacheMixin, JWTAuthMixin, reverse
from vng_api_common.tests.schema import get_spec

from zrc.datamodel.tests.factories import (
    ResultaatFactory,
    RolFactory,
    StatusFactory,
    ZaakEigenschapFactory,
    ZaakFactory,
    ZaakInformatieObjectFactory,
)
from zrc.tests.utils import ZAAK_READ_KWARGS

from .mixins import ZaakInformatieObjectSyncMixin


class ZaakCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zaak_get_cache_header(self):
        zaak = ZaakFactory.create()

        response = self.client.get(reverse(zaak), **ZAAK_READ_KWARGS)

        self.assertHasETag(response)

    def test_zaak_head_cache_header(self):
        zaak = ZaakFactory.create()

        self.assertHeadHasETag(reverse(zaak), **ZAAK_READ_KWARGS)

    def test_head_in_apischema(self):
        spec = get_spec()

        endpoint = spec["paths"]["/zaken/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        zaak = ZaakFactory.create(with_etag=True)

        response = self.client.get(
            reverse(zaak), HTTP_IF_NONE_MATCH=f'"{zaak._etag}"', **ZAAK_READ_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        zaak = ZaakFactory.create(with_etag=True)

        response = self.client.get(
            reverse(zaak), HTTP_IF_NONE_MATCH=f'"not-an-md5"', **ZAAK_READ_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ZaakCacheTransactionTests(JWTAuthMixin, APITransactionTestCase):
    heeft_alle_autorisaties = True

    def setUp(self):
        super().setUp()

        self._create_credentials(
            self.client_id,
            self.secret,
            self.heeft_alle_autorisaties,
            self.max_vertrouwelijkheidaanduiding,
        )

    def test_invalidate_new_status(self):
        """
        Status URL is part of the resource, so new status invalidates the ETag.
        """
        zaak = ZaakFactory.create(with_etag=True)
        etag = zaak._etag

        # create new status
        StatusFactory.create(zaak=zaak)

        response = self.client.get(
            reverse(zaak), HTTP_IF_NONE_MATCH=f'"{etag}"', **ZAAK_READ_KWARGS
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class StatusCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_status_get_cache_header(self):
        status_ = StatusFactory.create()

        response = self.client.get(reverse(status_))

        self.assertHasETag(response)

    def test_status_head_cache_header(self):
        status_ = StatusFactory.create()

        self.assertHeadHasETag(reverse(status_))

    def test_head_in_apischema(self):
        spec = get_spec()

        endpoint = spec["paths"]["/statussen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        """
        Test that, if I have a cached copy, the API returns an HTTP 304.
        """
        status_ = StatusFactory.create(with_etag=True)

        response = self.client.get(
            reverse(status_), HTTP_IF_NONE_MATCH=f'"{status_._etag}"'
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        status_ = StatusFactory.create(with_etag=True)

        response = self.client.get(reverse(status_), HTTP_IF_NONE_MATCH='"not-an-md5"')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ZaakInformatieObjectCacheTests(
    CacheMixin, ZaakInformatieObjectSyncMixin, JWTAuthMixin, APITestCase
):
    heeft_alle_autorisaties = True

    def test_zaakinformatieobject_get_cache_header(self):
        zaakinformatieobject = ZaakInformatieObjectFactory.create()

        response = self.client.get(reverse(zaakinformatieobject))

        self.assertHasETag(response)

    def test_zaakinformatieobject_head_cache_header(self):
        zaakinformatieobject = ZaakInformatieObjectFactory.create()

        self.assertHeadHasETag(reverse(zaakinformatieobject))

    def test_head_in_apischema(self):
        spec = get_spec()

        endpoint = spec["paths"]["/zaakinformatieobjecten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        zio = ZaakInformatieObjectFactory.create(with_etag=True)

        response = self.client.get(reverse(zio), HTTP_IF_NONE_MATCH=f'"{zio._etag}"')

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        zio = ZaakInformatieObjectFactory.create(with_etag=True)

        response = self.client.get(reverse(zio), HTTP_IF_NONE_MATCH='"old"')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ZaakEigenschapCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_zaakeigenschap_get_cache_header(self):
        zaakeigenschap = ZaakEigenschapFactory.create()

        response = self.client.get(
            reverse(zaakeigenschap, kwargs={"zaak_uuid": zaakeigenschap.zaak.uuid})
        )

        self.assertHasETag(response)

    def test_zaakeigenschap_head_cache_header(self):
        zaakeigenschap = ZaakEigenschapFactory.create()

        self.assertHeadHasETag(
            reverse(zaakeigenschap, kwargs={"zaak_uuid": zaakeigenschap.zaak.uuid})
        )

    def test_head_in_apischema(self):
        spec = get_spec()

        endpoint = spec["paths"]["/zaken/{zaak_uuid}/zaakeigenschappen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        zaak_eigenschap = ZaakEigenschapFactory.create(with_etag=True)

        response = self.client.get(
            reverse(zaak_eigenschap, kwargs={"zaak_uuid": zaak_eigenschap.zaak.uuid}),
            HTTP_IF_NONE_MATCH=f'"{zaak_eigenschap._etag}"',
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        zaak_eigenschap = ZaakEigenschapFactory.create(with_etag=True)

        response = self.client.get(
            reverse(zaak_eigenschap, kwargs={"zaak_uuid": zaak_eigenschap.zaak.uuid}),
            HTTP_IF_NONE_MATCH='"old"',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RolCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_rol_get_cache_header(self):
        rol = RolFactory.create()

        response = self.client.get(reverse(rol))

        self.assertHasETag(response)

    def test_rol_head_cache_header(self):
        rol = RolFactory.create()

        self.assertHeadHasETag(reverse(rol))

    def test_head_in_apischema(self):
        spec = get_spec()

        endpoint = spec["paths"]["/rollen/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        rol = RolFactory.create(with_etag=True)

        response = self.client.get(reverse(rol), HTTP_IF_NONE_MATCH=f'"{rol._etag}"')

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        rol = RolFactory.create(with_etag=True)

        response = self.client.get(reverse(rol), HTTP_IF_NONE_MATCH='"old"')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ResultaatCacheTests(CacheMixin, JWTAuthMixin, APITestCase):
    heeft_alle_autorisaties = True

    def test_resultaat_get_cache_header(self):
        resultaat = ResultaatFactory.create()

        response = self.client.get(reverse(resultaat))

        self.assertHasETag(response)

    def test_resultaat_head_cache_header(self):
        resultaat = ResultaatFactory.create()

        self.assertHeadHasETag(reverse(resultaat))

    def test_head_in_apischema(self):
        spec = get_spec()

        endpoint = spec["paths"]["/resultaten/{uuid}"]

        self.assertIn("head", endpoint)

    def test_conditional_get_304(self):
        resultaat = ResultaatFactory.create(with_etag=True)

        response = self.client.get(
            reverse(resultaat), HTTP_IF_NONE_MATCH=f'"{resultaat._etag}"'
        )

        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_conditional_get_stale(self):
        resultaat = ResultaatFactory.create(with_etag=True)

        response = self.client.get(reverse(resultaat), HTTP_IF_NONE_MATCH='"old"')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
