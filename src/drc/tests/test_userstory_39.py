"""
Test the flow described in https://github.com/VNG-Realisatie/gemma-zaken/issues/39
"""
import base64
from datetime import date
from urllib.parse import urlparse

from django.conf import settings

from rest_framework import status
from rest_framework.test import APITestCase
from zds_schema.tests import get_operation_url

from drc.datamodel.models import EnkelvoudigInformatieObject


class US39TestCase(APITestCase):

    def test_create_enkelvoudiginformatieobject(self):
        """
        Registreer een ENKELVOUDIGINFORMATIEOBJECT
        """
        url = get_operation_url('enkelvoudiginformatieobject_create')
        data = {
            'identificatie': 'AMS20180701001',
            'creatiedatum': '2018-07-01',
            'titel': 'text_extra.txt',
            'auteur': 'ANONIEM',
            'formaat': 'text/plain',
            'taal': 'nl',
            'inhoud': base64.b64encode(b'Extra tekst in bijlage').decode('utf-8'),
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn('identificatie', data)

        eio = EnkelvoudigInformatieObject.objects.get()
        self.assertEqual(eio.identificatie, 'AMS20180701001')
        self.assertEqual(eio.creatiedatum, date(2018, 7, 1))

        # should be a URL
        download_url = urlparse(response.data['inhoud'])
        self.assertTrue(download_url.path.startswith(settings.MEDIA_URL))
        self.assertTrue(download_url.path.endswith('.bin'))
