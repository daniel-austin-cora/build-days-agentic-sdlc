import http.cookiejar
import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dog_supply_store.app import DogStoreHTTPServer


class StoreHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.server = DogStoreHTTPServer(
            ("127.0.0.1", 0), Path(self.temporary_directory.name) / "store.sqlite3"
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        cookie_jar = http.cookiejar.CookieJar()
        self.client = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(cookie_jar)
        )

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary_directory.cleanup()

    def test_liveness_readiness_and_product_api(self):
        live = self.client.open(f"{self.base_url}/health/live")
        ready = self.client.open(f"{self.base_url}/health/ready")
        products = self.client.open(f"{self.base_url}/api/products")

        self.assertEqual(json.loads(live.read()), {"status": "alive"})
        self.assertEqual(json.loads(ready.read()), {"status": "ready"})
        self.assertGreaterEqual(len(json.loads(products.read())), 5)

    def test_store_page_has_accessible_forms_and_simulated_checkout(self):
        page = self.client.open(self.base_url).read().decode()
        token = self._csrf_token(page)
        self.assertIn("<h1>", page)
        self.assertIn('aria-label="Main navigation"', page)
        self.assertIn("No card details, real money", page)

        response = self._post(
            "/cart/add",
            {"csrf_token": token, "product_id": "squeaky-duck", "quantity": "2"},
        )
        self.assertIn("Your pack (1 item types)", response)
        self.assertIn("16 treat tokens", response)

        order_page = self._post(
            "/checkout",
            {"csrf_token": self._csrf_token(response), "dog_name": "Lady Floof"},
        )
        self.assertIn("Checkout complete (in our imaginations)", order_page)
        self.assertIn("Lady Floof", order_page)
        self.assertIn("payment details were involved", order_page)
        self.assertNotIn("type=\"password\"", order_page)

    def test_checkout_requires_a_valid_csrf_token(self):
        page = self.client.open(self.base_url).read().decode()
        request = urllib.request.Request(
            f"{self.base_url}/checkout",
            data=urllib.parse.urlencode({"dog_name": "Good Dog"}).encode(),
            method="POST",
        )

        with self.assertRaises(urllib.error.HTTPError) as error:
            self.client.open(request)
        self.assertEqual(error.exception.code, 403)
        response_body = error.exception.read().decode()
        error.exception.close()
        self.assertIn("fresh sniff of approval", response_body)
        self.assertTrue(self._csrf_token(page))

    def test_invalid_quantity_returns_a_helpful_validation_error(self):
        page = self.client.open(self.base_url).read().decode()
        request = urllib.request.Request(
            f"{self.base_url}/cart/add",
            data=urllib.parse.urlencode(
                {
                    "csrf_token": self._csrf_token(page),
                    "product_id": "squeaky-duck",
                    "quantity": "many",
                }
            ).encode(),
            method="POST",
        )

        with self.assertRaises(urllib.error.HTTPError) as error:
            self.client.open(request)
        self.assertEqual(error.exception.code, 400)
        response_body = error.exception.read().decode()
        error.exception.close()
        self.assertIn("whole number", response_body)

    def test_customer_supplied_name_is_escaped_in_confirmation(self):
        page = self.client.open(self.base_url).read().decode()
        page = self._post(
            "/cart/add",
            {
                "csrf_token": self._csrf_token(page),
                "product_id": "tennis-ball",
                "quantity": "1",
            },
        )
        order_page = self._post(
            "/checkout",
            {
                "csrf_token": self._csrf_token(page),
                "dog_name": "<script>alert(1)</script>",
            },
        )

        self.assertIn("&lt;script&gt;", order_page)
        self.assertNotIn("<script>alert(1)</script>", order_page)

    def _post(self, path, fields):
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=urllib.parse.urlencode(fields).encode(),
            method="POST",
        )
        return self.client.open(request).read().decode()

    @staticmethod
    def _csrf_token(page):
        match = re.search(r'name="csrf_token" value="([^"]+)"', page)
        if match is None:
            raise AssertionError("The page did not provide a CSRF token.")
        return match.group(1)


if __name__ == "__main__":
    unittest.main()
