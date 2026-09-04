import tempfile
import unittest
from pathlib import Path

from backend.storage import DuplicateEndpointError, Store


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp_directory.name) / "test.db")

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_store_endpoint_and_check(self):
        endpoint = self.store.add_endpoint("Example", "https://example.com")
        self.store.add_check(
            endpoint["id"],
            {
                "checked_at": "2026-09-03T12:00:00+00:00",
                "status": "online",
                "status_code": 200,
                "response_time_ms": 123.4,
            },
        )
        service = self.store.list_services()[0]
        self.assertEqual(service["name"], "Example")
        self.assertEqual(service["history"][0]["status_code"], 200)
        self.assertEqual(service["history"][0]["response_time_ms"], 123.4)

    def test_store_prevents_duplicate_urls(self):
        self.store.add_endpoint("First", "https://example.com")
        with self.assertRaises(DuplicateEndpointError):
            self.store.add_endpoint("Duplicate", "https://example.com")

    def test_delete_endpoint_cascades_checks(self):
        endpoint = self.store.add_endpoint("Example", "https://example.com")
        self.store.add_check(
            endpoint["id"],
            {
                "checked_at": "2026-09-03T12:00:00+00:00",
                "status": "offline",
                "status_code": 503,
                "response_time_ms": 250.0,
                "error": "HTTP 503",
            },
        )
        self.assertTrue(self.store.delete_endpoint(endpoint["id"]))
        self.assertEqual(self.store.list_services(), [])


if __name__ == "__main__":
    unittest.main()
