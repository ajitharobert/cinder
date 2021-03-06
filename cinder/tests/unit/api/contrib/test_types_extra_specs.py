# Copyright (c) 2011 Zadara Storage Inc.
# Copyright (c) 2011 OpenStack Foundation
# Copyright 2011 University of Southern California
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from unittest import mock

import ddt
from oslo_config import cfg
from oslo_utils import timeutils
import webob

from cinder.api.contrib import types_extra_specs
from cinder import exception
from cinder.image import glance as image_store
from cinder.tests.unit.api import fakes
from cinder.tests.unit import fake_constants as fake
from cinder.tests.unit import test
import cinder.wsgi

CONF = cfg.CONF


def return_create_volume_type_extra_specs(context, volume_type_id,
                                          extra_specs):
    return fake_volume_type_extra_specs()


def return_volume_type_extra_specs(context, volume_type_id):
    return fake_volume_type_extra_specs()


def return_volume_type(context, volume_type_id, expected_fields=None):
    specs = {"key1": "value1",
             "key2": "value2",
             "key3": "value3",
             "key4": "value4",
             "key5": "value5"}
    return dict(id=id,
                name='vol_type_%s' % id,
                description='vol_type_desc_%s' % id,
                extra_specs=specs,
                created_at=timeutils.utcnow(),
                updated_at=timeutils.utcnow(),
                deleted_at=timeutils.utcnow())


def fake_volume_type_extra_specs():
    specs = {"key1": "value1",
             "key2": "value2",
             "key3": "value3",
             "key4": "value4",
             "key5": "value5"}
    return specs


@ddt.ddt
class VolumeTypesExtraSpecsTest(test.TestCase):

    def setUp(self):
        super(VolumeTypesExtraSpecsTest, self).setUp()
        self.flags(host='fake')
        self.mock_object(cinder.db, 'volume_type_get', return_volume_type)
        self.api_path = '/v2/%s/os-volume-types/%s/extra_specs' % (
            fake.PROJECT_ID, fake.VOLUME_TYPE_ID)
        self.controller = types_extra_specs.VolumeTypeExtraSpecsController()

        """to reset notifier drivers left over from other api/contrib tests"""

    def test_index(self):
        self.mock_object(cinder.db, 'volume_type_extra_specs_get',
                         return_volume_type_extra_specs)

        req = fakes.HTTPRequest.blank(self.api_path)
        res_dict = self.controller.index(req, fake.VOLUME_TYPE_ID)

        self.assertEqual('value1', res_dict['extra_specs']['key1'])

    def test_index_no_data(self):
        self.mock_object(cinder.db, 'volume_type_extra_specs_get',
                         return_value={})

        req = fakes.HTTPRequest.blank(self.api_path)
        res_dict = self.controller.index(req, fake.VOLUME_TYPE_ID)

        self.assertEqual(0, len(res_dict['extra_specs']))

    def test_show(self):
        self.mock_object(cinder.db, 'volume_type_extra_specs_get',
                         return_volume_type_extra_specs)

        req = fakes.HTTPRequest.blank(self.api_path + '/key5')
        res_dict = self.controller.show(req, fake.VOLUME_TYPE_ID, 'key5')

        self.assertEqual('value5', res_dict['key5'])

    def test_show_spec_not_found(self):
        self.mock_object(cinder.db, 'volume_type_extra_specs_get',
                         return_value={})

        req = fakes.HTTPRequest.blank(self.api_path + '/key6')
        self.assertRaises(exception.VolumeTypeExtraSpecsNotFound,
                          self.controller.show, req, fake.VOLUME_ID, 'key6')

    def test_delete(self):
        self.mock_object(cinder.db, 'volume_type_extra_specs_delete')

        self.assertEqual(0, len(self.notifier.notifications))
        req = fakes.HTTPRequest.blank(self.api_path + '/key5')
        self.controller.delete(req, fake.VOLUME_ID, 'key5')
        self.assertEqual(1, len(self.notifier.notifications))
        self.assertIn('created_at', self.notifier.notifications[0]['payload'])
        self.assertIn('updated_at', self.notifier.notifications[0]['payload'])
        self.assertIn('deleted_at', self.notifier.notifications[0]['payload'])

    def test_delete_not_found(self):
        self.mock_object(cinder.db, 'volume_type_extra_specs_delete',
                         side_effect=exception.VolumeTypeExtraSpecsNotFound(
                             "Not Found"))

        req = fakes.HTTPRequest.blank(self.api_path + '/key6')
        self.assertRaises(exception.VolumeTypeExtraSpecsNotFound,
                          self.controller.delete, req, fake.VOLUME_ID, 'key6')

    def test_create(self):
        self.mock_object(cinder.db,
                         'volume_type_extra_specs_update_or_create',
                         return_create_volume_type_extra_specs)
        body = {"extra_specs": {"key1": "value1"}}

        self.assertEqual(0, len(self.notifier.notifications))
        req = fakes.HTTPRequest.blank(self.api_path)
        res_dict = self.controller.create(req, fake.VOLUME_ID, body=body)
        self.assertEqual(1, len(self.notifier.notifications))
        self.assertIn('created_at', self.notifier.notifications[0]['payload'])
        self.assertIn('updated_at', self.notifier.notifications[0]['payload'])
        self.assertEqual('value1', res_dict['extra_specs']['key1'])

    @mock.patch.object(image_store.GlanceImageService, 'get_stores')
    def test_create_valid_image_store(self, mock_get_stores):
        mock_get_stores.return_value = {
            'stores': [{
                'default': 'true',
                'id': 'cheap'
            }, {
                'id': 'read_only_store',
                'read-only': 'true'
            }]
        }
        self.mock_object(cinder.db,
                         'volume_type_extra_specs_update_or_create',
                         return_create_volume_type_extra_specs)
        body = {"extra_specs": {"image_service:store_id": "cheap"}}

        self.assertEqual(0, len(self.notifier.notifications))
        req = fakes.HTTPRequest.blank(self.api_path)
        res_dict = self.controller.create(req, fake.VOLUME_ID, body=body)
        self.assertEqual(1, len(self.notifier.notifications))
        self.assertIn('created_at', self.notifier.notifications[0]['payload'])
        self.assertIn('updated_at', self.notifier.notifications[0]['payload'])
        self.assertEqual(
            'cheap', res_dict['extra_specs']['image_service:store_id'])

    @mock.patch.object(image_store.GlanceImageService, 'get_stores')
    def test_create_invalid_image_store(self, mock_get_stores):
        mock_get_stores.return_value = {
            'stores': [{
                'default': 'true',
                'id': 'cheap'
            }, {
                'id': 'read_only_store',
                'read-only': 'true'
            }]
        }
        body = {"extra_specs": {"image_service:store_id": "fast"}}
        req = fakes.HTTPRequest.blank(self.api_path)
        self.assertRaises(cinder.exception.GlanceStoreNotFound,
                          self.controller.create,
                          req, fake.VOLUME_ID, body=body)

    @mock.patch.object(image_store.GlanceImageService, 'get_stores')
    def test_create_read_only_image_store(self, mock_get_stores):
        mock_get_stores.return_value = {
            'stores': [{
                'default': 'true',
                'id': 'cheap'
            }, {
                'id': 'read_only_store',
                'read-only': 'true'
            }]
        }
        body = {"extra_specs": {"image_service:store_id": "read_only_store"}}
        req = fakes.HTTPRequest.blank(self.api_path)
        self.assertRaises(cinder.exception.GlanceStoreReadOnly,
                          self.controller.create,
                          req, fake.VOLUME_ID, body=body)

    @mock.patch.object(cinder.db, 'volume_type_extra_specs_update_or_create')
    def test_create_key_allowed_chars(
            self, volume_type_extra_specs_update_or_create):
        mock_return_value = {"key1": "value1",
                             "key2": "value2",
                             "key3": "value3",
                             "key4": "value4",
                             "key5": "value5"}
        volume_type_extra_specs_update_or_create.\
            return_value = mock_return_value

        body = {"extra_specs": {"other_alphanum.-_:": "value1"}}

        self.assertEqual(0, len(self.notifier.notifications))

        req = fakes.HTTPRequest.blank(self.api_path)
        res_dict = self.controller.create(req, fake.VOLUME_ID, body=body)
        self.assertEqual(1, len(self.notifier.notifications))
        self.assertEqual('value1',
                         res_dict['extra_specs']['other_alphanum.-_:'])

    @mock.patch.object(cinder.db, 'volume_type_extra_specs_update_or_create')
    def test_create_too_many_keys_allowed_chars(
            self, volume_type_extra_specs_update_or_create):
        mock_return_value = {"key1": "value1",
                             "key2": "value2",
                             "key3": "value3",
                             "key4": "value4",
                             "key5": "value5"}
        volume_type_extra_specs_update_or_create.\
            return_value = mock_return_value

        body = {"extra_specs": {"other_alphanum.-_:": "value1",
                                "other2_alphanum.-_:": "value2",
                                "other3_alphanum.-_:": "value3"}}

        self.assertEqual(0, len(self.notifier.notifications))

        req = fakes.HTTPRequest.blank(self.api_path)
        res_dict = self.controller.create(req, fake.VOLUME_ID, body=body)
        self.assertEqual(1, len(self.notifier.notifications))
        self.assertEqual('value1',
                         res_dict['extra_specs']['other_alphanum.-_:'])
        self.assertEqual('value2',
                         res_dict['extra_specs']['other2_alphanum.-_:'])
        self.assertEqual('value3',
                         res_dict['extra_specs']['other3_alphanum.-_:'])

    @mock.patch.object(image_store.GlanceImageService, 'get_stores')
    def test_update_valid_image_store(self, mock_get_stores):
        mock_get_stores.return_value = {
            'stores': [{
                'default': 'true',
                'id': 'cheap'
            }, {
                'id': 'fast',
            },
                {
                'id': 'read_only_store',
                'read-only': 'true'
            }]
        }
        self.mock_object(cinder.db,
                         'volume_type_extra_specs_update_or_create',
                         return_create_volume_type_extra_specs)
        body = {"image_service:store_id": "fast"}

        self.assertEqual(0, len(self.notifier.notifications))
        req = fakes.HTTPRequest.blank(
            self.api_path + "/image_service:store_id")
        res_dict = self.controller.update(req, fake.VOLUME_ID,
                                          "image_service:store_id",
                                          body=body)
        self.assertEqual(1, len(self.notifier.notifications))
        self.assertIn('created_at', self.notifier.notifications[0]['payload'])
        self.assertIn('updated_at', self.notifier.notifications[0]['payload'])
        self.assertEqual(
            'fast', res_dict['image_service:store_id'])

    @mock.patch.object(image_store.GlanceImageService, 'get_stores')
    def test_update_invalid_image_store(self, mock_get_stores):
        mock_get_stores.return_value = {
            'stores': [{
                'default': 'true',
                'id': 'cheap'
            }, {
                'id': 'fast',
            },
                {
                'id': 'read_only_store',
                'read-only': 'true'
            }]
        }
        self.mock_object(cinder.db,
                         'volume_type_extra_specs_update_or_create',
                         return_create_volume_type_extra_specs)
        body = {"image_service:store_id": "very_fast"}

        self.assertEqual(0, len(self.notifier.notifications))
        req = fakes.HTTPRequest.blank(
            self.api_path + "/image_service:store_id")
        self.assertRaises(cinder.exception.GlanceStoreNotFound,
                          self.controller.update,
                          req, fake.VOLUME_ID,
                          "image_service:store_id",
                          body=body)

    @mock.patch.object(image_store.GlanceImageService, 'get_stores')
    def test_update_read_only_image_store(self, mock_get_stores):
        mock_get_stores.return_value = {
            'stores': [{
                'default': 'true',
                'id': 'cheap'
            }, {
                'id': 'fast',
            },
                {
                'id': 'read_only_store',
                'read-only': 'true'
            }]
        }
        self.mock_object(cinder.db,
                         'volume_type_extra_specs_update_or_create',
                         return_create_volume_type_extra_specs)
        body = {"image_service:store_id": "read_only_store"}

        self.assertEqual(0, len(self.notifier.notifications))
        req = fakes.HTTPRequest.blank(
            self.api_path + "/image_service:store_id")
        self.assertRaises(cinder.exception.GlanceStoreReadOnly,
                          self.controller.update,
                          req, fake.VOLUME_ID,
                          "image_service:store_id",
                          body=body)

    def test_update_item(self):
        self.mock_object(cinder.db,
                         'volume_type_extra_specs_update_or_create',
                         return_create_volume_type_extra_specs)
        body = {"key1": "value1"}

        self.assertEqual(0, len(self.notifier.notifications))
        req = fakes.HTTPRequest.blank(self.api_path + '/key1')
        res_dict = self.controller.update(req, fake.VOLUME_ID, 'key1',
                                          body=body)
        self.assertEqual(1, len(self.notifier.notifications))
        self.assertIn('created_at', self.notifier.notifications[0]['payload'])
        self.assertIn('updated_at', self.notifier.notifications[0]['payload'])

        self.assertEqual('value1', res_dict['key1'])

    def test_update_item_too_many_keys(self):
        self.mock_object(cinder.db,
                         'volume_type_extra_specs_update_or_create',
                         return_create_volume_type_extra_specs)
        body = {"key1": "value1", "key2": "value2"}

        req = fakes.HTTPRequest.blank(self.api_path + '/key1')
        self.assertRaises(exception.ValidationError, self.controller.update,
                          req, fake.VOLUME_ID, 'key1', body=body)

    def test_update_item_body_uri_mismatch(self):
        self.mock_object(cinder.db,
                         'volume_type_extra_specs_update_or_create',
                         return_create_volume_type_extra_specs)
        body = {"key1": "value1"}

        req = fakes.HTTPRequest.blank(self.api_path + '/bad')
        self.assertRaises(webob.exc.HTTPBadRequest, self.controller.update,
                          req, fake.VOLUME_ID, 'bad', body=body)

    def _extra_specs_empty_update(self, body):
        req = fakes.HTTPRequest.blank('/v2/%s/types/%s/extra_specs' % (
            fake.PROJECT_ID, fake.VOLUME_TYPE_ID))
        req.method = 'POST'

        self.assertRaises(exception.ValidationError,
                          self.controller.update, req, fake.VOLUME_ID,
                          body=body)

    def test_update_no_body(self):
        self._extra_specs_empty_update(body=None)

    def test_update_empty_body(self):
        self._extra_specs_empty_update(body={})

    def _extra_specs_create_bad_body(self, body):
        req = fakes.HTTPRequest.blank('/v2/%s/types/%s/extra_specs' % (
            fake.PROJECT_ID, fake.VOLUME_TYPE_ID))
        req.method = 'POST'

        self.assertRaises(exception.ValidationError,
                          self.controller.create, req, fake.VOLUME_ID,
                          body=body)

    def test_create_no_body(self):
        self._extra_specs_create_bad_body(body=None)

    def test_create_missing_volume(self):
        body = {'foo': {'a': 'b'}}
        self._extra_specs_create_bad_body(body=body)

    def test_create_malformed_entity(self):
        body = {'extra_specs': 'string'}
        self._extra_specs_create_bad_body(body=body)

    def test_create_invalid_key(self):
        body = {"extra_specs": {"ke/y1": "value1"}}
        self._extra_specs_create_bad_body(body=body)

    def test_create_invalid_too_many_key(self):
        body = {"key1": "value1", "ke/y2": "value2", "key3": "value3"}
        self._extra_specs_create_bad_body(body=body)

    def test_create_volumes_exist(self):
        self.mock_object(cinder.db,
                         'volume_type_extra_specs_update_or_create',
                         return_create_volume_type_extra_specs)
        body = {"extra_specs": {"key1": "value1"}}
        req = fakes.HTTPRequest.blank(self.api_path)
        with mock.patch.object(
                cinder.db,
                'volume_get_all',
                return_value=['a']):
            req = fakes.HTTPRequest.blank('/v2/%s/types/%s/extra_specs' % (
                fake.PROJECT_ID, fake.VOLUME_TYPE_ID))
            req.method = 'POST'

            body = {"extra_specs": {"key1": "value1"}}
            req = fakes.HTTPRequest.blank(self.api_path)
            self.assertRaises(webob.exc.HTTPBadRequest,
                              self.controller.create,
                              req,
                              fake.VOLUME_ID, body=body)

    @ddt.data({'extra_specs': {'a' * 256: 'a'}},
              {'extra_specs': {'a': 'a' * 256}},
              {'extra_specs': {'': 'a'}},
              {'extra_specs': {'     ': 'a'}})
    def test_create_with_invalid_extra_specs(self, body):
        req = fakes.HTTPRequest.blank('/v2/%s/types/%s/extra_specs' % (
            fake.PROJECT_ID, fake.VOLUME_TYPE_ID))
        req.method = 'POST'

        self.assertRaises(exception.ValidationError,
                          self.controller.create, req, fake.VOLUME_ID,
                          body=body)
