import tempfile
import unittest
from pathlib import Path

from dog_supply_store.storage import DogStore


class DogStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.store = DogStore(Path(self.temporary_directory.name) / "store.sqlite3")
        self.store.create_session("session-one", "csrf-one")

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_catalog_is_seeded_and_has_dog_focused_products(self):
        products = self.store.list_products()

        self.assertGreaterEqual(len(products), 5)
        self.assertTrue(any("Squeaky" in str(product["name"]) for product in products))

    def test_cart_addition_totals_and_removal(self):
        self.store.add_to_cart("session-one", "squeaky-duck", 2)

        cart = self.store.get_cart("session-one")
        self.assertEqual(len(cart), 1)
        self.assertEqual(cart[0]["quantity"], 2)
        self.assertEqual(cart[0]["subtotal"], 16)

        self.store.remove_from_cart("session-one", "squeaky-duck")
        self.assertEqual(self.store.get_cart("session-one"), [])

    def test_cart_rejects_unknown_products_and_excessive_quantities(self):
        with self.assertRaisesRegex(ValueError, "vanished behind the sofa"):
            self.store.add_to_cart("session-one", "invisible-squirrel", 1)
        with self.assertRaisesRegex(ValueError, "between 1 and 20"):
            self.store.add_to_cart("session-one", "squeaky-duck", 21)

    def test_checkout_records_a_simulated_order_and_empties_the_cart(self):
        self.store.add_to_cart("session-one", "squeaky-duck", 2)
        order = self.store.create_order("session-one", "Lady Floof")

        self.assertEqual(order["dog_name"], "Lady Floof")
        self.assertEqual(order["total_tokens"], 16)
        self.assertEqual(order["payment_status"], "SIMULATED")
        self.assertEqual(len(str(order["id"])), 12)
        self.assertEqual(self.store.get_cart("session-one"), [])
        persisted_order = self.store.get_order(str(order["id"]))
        self.assertIsNotNone(persisted_order)
        self.assertEqual(persisted_order["dog_name"], "Lady Floof")
        self.assertEqual(persisted_order["items"][0]["quantity"], 2)

    def test_checkout_rejects_an_empty_pack(self):
        with self.assertRaisesRegex(ValueError, "pack is empty"):
            self.store.create_order("session-one", "Good Dog")

    def test_cart_and_session_data_are_separate(self):
        self.store.create_session("session-two", "csrf-two")
        self.store.add_to_cart("session-one", "tennis-ball", 1)

        self.assertEqual(len(self.store.get_cart("session-one")), 1)
        self.assertEqual(self.store.get_cart("session-two"), [])


if __name__ == "__main__":
    unittest.main()
