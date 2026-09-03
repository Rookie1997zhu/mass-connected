"""Unit tests for OSS-compatible media URL and local path helpers."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import SimpleTestCase, override_settings

from core.media_urls import absolute_file_url, absolute_media_url
from core.storage_utils import local_file_path, materialize_field_file


class AbsoluteMediaUrlTests(SimpleTestCase):
    def test_keeps_absolute_https(self):
        request = MagicMock()
        url = "https://bucket.oss-ap-northeast-2.aliyuncs.com/a.pdf?Expires=1&Signature=x"
        self.assertEqual(absolute_media_url(request, url), url)
        request.build_absolute_uri.assert_not_called()

    def test_prefixes_relative(self):
        request = MagicMock()
        request.build_absolute_uri.return_value = "http://localhost/media/a.pdf"
        self.assertEqual(absolute_media_url(request, "/media/a.pdf"), "http://localhost/media/a.pdf")
        request.build_absolute_uri.assert_called_once_with("/media/a.pdf")

    def test_absolute_file_url_empty(self):
        self.assertEqual(absolute_file_url(None, None), "")


class StorageUtilsTests(SimpleTestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="oss_storage_test_"))
        self.media = self.tmp / "media"
        self.media.mkdir(parents=True, exist_ok=True)
        self.storage = FileSystemStorage(location=str(self.media))

    def test_materialize_local_uses_path(self):
        with override_settings(MEDIA_ROOT=str(self.media)):
            name = self.storage.save("uploads/hello.txt", ContentFile(b"hello"))
            field = MagicMock()
            field.name = name
            field.path = str(Path(self.media) / name)

            path = materialize_field_file(field)
            self.assertEqual(path, field.path)
            self.assertTrue(os.path.isfile(path))

    def test_materialize_remote_copies_under_media(self):
        with override_settings(MEDIA_ROOT=str(self.media)):
            field = MagicMock()
            field.name = "remote/doc.bin"

            def _raise_path():
                raise NotImplementedError()

            type(field).path = property(lambda self: _raise_path())

            from io import BytesIO

            field.open = lambda mode="rb": BytesIO(b"payload")

            path = materialize_field_file(field)
            self.assertTrue(path.startswith(str(self.media)))
            self.assertTrue(os.path.isfile(path))
            with open(path, "rb") as fh:
                self.assertEqual(fh.read(), b"payload")

    def test_local_file_path_remote_cleans_temp(self):
        with override_settings(MEDIA_ROOT=str(self.media)):
            field = MagicMock()
            field.name = "remote/doc.bin"

            def _raise_path():
                raise NotImplementedError()

            type(field).path = property(lambda self: _raise_path())

            from io import BytesIO

            field.open = lambda mode="rb": BytesIO(b"payload")

            with local_file_path(field) as path:
                self.assertTrue(os.path.isfile(path))
                with open(path, "rb") as fh:
                    self.assertEqual(fh.read(), b"payload")
            self.assertFalse(os.path.exists(path))
