import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from main import app


class CacheAdminTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = Path.cwd()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        os.chdir(self.directory.name)
        self.addCleanup(os.chdir, self.original_cwd)
        Path("cache").mkdir()
        Path("cache/sentinel.txt").write_text("cached result")
        self.environment = patch.dict(os.environ, {"CACHE_ADMIN_PASSWORD": ""})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = app.test_client()

    def assert_cache_preserved(self):
        self.assertEqual(Path("cache/sentinel.txt").read_text(), "cached result")

    def test_unset_admin_password_disables_cache_clearing(self):
        os.environ.pop("CACHE_ADMIN_PASSWORD", None)
        response = self.client.post("/api/clear-cache", json={"password": "anything"})
        self.assertEqual(response.status_code, 503)
        self.assert_cache_preserved()

    def test_empty_admin_password_disables_cache_clearing(self):
        response = self.client.post("/api/clear-cache", json={"password": ""})
        self.assertEqual(response.status_code, 503)
        self.assert_cache_preserved()

    def test_wrong_admin_password_preserves_cache(self):
        os.environ["CACHE_ADMIN_PASSWORD"] = "configured-test-password"
        response = self.client.post("/api/clear-cache", json={"password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assert_cache_preserved()

    def test_missing_and_non_string_passwords_are_rejected(self):
        os.environ["CACHE_ADMIN_PASSWORD"] = "configured-test-password"
        for body in ({}, [], None, {"password": None}, {"password": 123}, {"password": []}):
            with self.subTest(body=body):
                response = self.client.post("/api/clear-cache", json=body)
                self.assertEqual(response.status_code, 401)
                self.assert_cache_preserved()

    def test_malformed_json_is_rejected(self):
        os.environ["CACHE_ADMIN_PASSWORD"] = "configured-test-password"
        response = self.client.post(
            "/api/clear-cache", data="{", content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)
        self.assert_cache_preserved()

    def test_configured_password_clears_cache(self):
        os.environ["CACHE_ADMIN_PASSWORD"] = "configured-test-password"
        response = self.client.post(
            "/api/clear-cache", json={"password": "configured-test-password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"message": "Cache cleared successfully"})
        self.assertTrue(Path("cache").is_dir())
        self.assertEqual(list(Path("cache").iterdir()), [])

    def test_unicode_configured_password_is_supported(self):
        os.environ["CACHE_ADMIN_PASSWORD"] = "test-password-\u00e9"
        response = self.client.post(
            "/api/clear-cache", json={"password": "test-password-\u00e9"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(Path("cache").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
