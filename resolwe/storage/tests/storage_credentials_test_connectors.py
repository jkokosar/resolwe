# pylint: disable=missing-docstring
import io
import os
import shutil
import tempfile

from django.conf import settings
from django.test import override_settings

from resolwe.storage.connectors import (
    AwsS3Connector,
    GoogleConnector,
    LocalFilesystemConnector,
    connectors,
)
from resolwe.storage.connectors.baseconnector import BaseStorageConnector
from resolwe.storage.connectors.hasher import StreamHasher
from resolwe.test import TestCase

CONNECTORS_SETTINGS = {
    "local": {
        "connector": "resolwe.storage.connectors.localconnector.LocalFilesystemConnector",
        "config": {"path": "/my/path"},
    },
    "S3": {
        "connector": "resolwe.storage.connectors.s3connector.AwsS3Connector",
        "config": {
            "bucket": "genialis-test-storage",
            "credentials": os.path.join(
                settings.PROJECT_ROOT, "testing_credentials_s3.json"
            ),
        },
    },
    "GCS": {
        "connector": "resolwe.storage.connectors.googleconnector.GoogleConnector",
        "config": {
            "bucket": "genialis_storage_test",
            "credentials": os.path.join(
                settings.PROJECT_ROOT, "testing_credentials_gcs.json"
            ),
        },
    },
}


def create_file(name, size):
    with open(name, "wb") as f:
        f.seek(size - 1)
        f.write(b"\0")
        f.seek(0)
        f.write(name.encode("utf-8"))


def hashes(filename):
    hasher = StreamHasher()
    with open(filename, "rb") as stream:
        hasher.compute(stream)
    return {type_: hasher.hexdigest(type_) for type_ in ["awss3etag", "md5", "crc32c"]}


class RegistryTest(TestCase):
    def setUp(self):
        with override_settings(STORAGE_CONNECTORS=CONNECTORS_SETTINGS):
            connectors.recreate_connectors()

    def tearDown(self):
        connectors.recreate_connectors()

    def test_instance_from_settings(self):

        self.assertIn("local", connectors)
        self.assertIn("S3", connectors)
        self.assertIn("GCS", connectors)
        for connector_name in connectors:
            connector = connectors[connector_name]
            self.assertIsInstance(connector, BaseStorageConnector)


class TestMixin:
    """Tests for all storage connectors."""

    def test_exists(self):
        for file_ in self.created_files:
            self.assertTrue(self.connector.exists(file_))
        self.assertFalse(self.connector.exists(self.prefix_name("nonexisting_file")))

    def test_list_objects(self):
        files = self.connector.get_object_list(self.url_prefix)
        self.assertEqual(len(files), len(self.created_files))
        for file_ in self.created_files:
            self.assertIn(file_, files)
        self.assertEqual(
            self.connector.get_object_list(self.prefix_name("dir")),
            [self.prefix_name("dir/3")],
        )
        self.assertEqual(
            self.connector.get_object_list(self.prefix_name("nonexisting_directory")),
            [],
        )

    def test_delete(self):
        self.connector.delete([self.prefix_name("nonexisting_file")])
        files = self.connector.get_object_list(self.url_prefix)
        for file_ in self.created_files:
            self.assertIn(file_, files)
        self.connector.delete(self.created_files[:2])
        files = self.connector.get_object_list(self.url_prefix)
        self.assertEqual(files, [self.created_files[2]])

    def test_get(self):
        stream = io.BytesIO()
        starts_with = self.path(self.created_files[0]).encode("utf-8")
        self.connector.get(self.created_files[0], stream)
        self.assertEqual(stream.tell(), 1024 * 1024)
        stream.seek(0)
        self.assertEqual(stream.read(len(starts_with)), starts_with)
        self.assertEqual(stream.read(), b"\0" * (1024 * 1024 - len(starts_with)))

    def test_push(self):
        transfer_file = self.prefix_name("transfer")
        with open(self.path(self.created_files[0]), "rb") as f:
            self.connector.push(f, transfer_file)
        self.assertTrue(self.connector.exists(transfer_file))

        downloaded_file = self.prefix_name("download")
        with open(self.path(downloaded_file), "wb") as stream:
            self.connector.get(transfer_file, stream)

        with open(self.path(self.created_files[0]), "rb") as f1:
            with open(self.path(downloaded_file), "rb") as f2:
                self.assertEqual(f1.read(), f2.read())

        self.connector.delete([transfer_file])

    def test_get_hash(self):
        test_file = self.created_files[0]
        computed_hashes = hashes(self.path(test_file))
        for type_ in ("md5", "crc32c"):
            self.assertEqual(
                self.connector.get_hash(test_file, type_).lower(),
                computed_hashes[type_].lower(),
            )
            self.assertEqual(
                self.connector.get_hash(test_file, type_).lower(),
                computed_hashes[type_].lower(),
            )


class BaseTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        setattr(cls, "tmp_dir", tempfile.TemporaryDirectory())
        local_settings = CONNECTORS_SETTINGS["local"]["config"].copy()
        local_settings["path"] = cls.tmp_dir.name
        cls.local = LocalFilesystemConnector(local_settings, "local")
        cls.gcs = GoogleConnector(CONNECTORS_SETTINGS["GCS"]["config"], "GCS")
        cls.s3 = AwsS3Connector(CONNECTORS_SETTINGS["S3"]["config"], "S3")

    def _purge_tmp_dir(self):
        for root, dirs, files in os.walk(self.tmp_dir.name):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))

    def setUp(self):
        self._purge_tmp_dir()
        os.makedirs(os.path.join(self.tmp_dir.name, self.url_prefix, "dir"))

        self.created_files = [
            os.path.join(self.url_prefix, name) for name in ("1", "2", "dir/3")
        ]
        for file_ in self.created_files:
            create_file(self.path(file_), 1024 * 1024)

        return super().setUp()

    def path(self, filename):
        return os.path.join(self.tmp_dir.name, filename)

    def prefix_name(self, filename):
        return os.path.join(self.url_prefix, filename)


class LocalConnectorTest(BaseTestCase, TestMixin):
    def setUp(self):
        self.url_prefix = "local_connector_test"
        self.connector = self.local
        super().setUp()


class GoogleConnectorTest(BaseTestCase, TestMixin):
    def setUp(self):
        self.url_prefix = "google_connector_test"
        self.connector = self.gcs
        super().setUp()
        # Use connector to push files to storage for testing.
        # If this does not work tests will fail anyway.
        for file_ in self.created_files:
            if not self.gcs.exists(file_):
                with open(self.path(file_), "rb") as stream:
                    self.gcs.push(stream, file_)


class S3ConnectorTest(BaseTestCase):
    def setUp(self):
        self.url_prefix = "s3_connector_test"
        self.connector = self.s3
        super().setUp()
        # Use connector to push files to storage for testing.
        # If this does not work tests will fail anyway.
        for file_ in self.created_files:
            if not self.s3.exists(file_):
                with open(self.path(file_), "rb") as stream:
                    self.s3.push(stream, file_)
