"""Meaningful price watcher tests; all network traffic stays on a local fixture server."""
from copy import deepcopy
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlparse

from price_monitor import exact_card, cents_price, offers_from_product, run


TITLE = "Nico Robin (010) (Alternate Art) [EB05-010] Extra Booster: One Piece Heroines Edition Vol. 2 (Foil)"
NOW = "2026-11-14T15:00:00+00:00"
LATER = "2026-11-14T15:30:00+00:00"
PRODUCT = {"id": 123, "title": TITLE, "variants": [
    {"id": 10, "title": "Near Mint Foil", "price": 4900, "available": True},
    {"id": 11, "title": "Lightly Played Foil", "price": 3500, "available": False},
]}


class FixtureHandler(BaseHTTPRequestHandler):
    routes = {}
    hits = []

    def do_GET(self):
        path = urlparse(self.path).path
        type(self).hits.append(path)
        status, body = type(self).routes.get(path, (404, {}))
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_):
        pass


class PriceWatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        FixtureHandler.routes = {
            "/cart.js": (200, {"currency": "CAD"}),
            "/search/suggest.json": (200, {"resources": {"results": {"products": [
                {"title": TITLE, "url": "/products/robin"},
                {"title": "Nico Robin [EB05-010] Regular Art", "url": "/products/regular"},
                {"title": TITLE, "url": "https://unrelated.example/products/fake"},
            ]}}}),
            "/products/robin.js": (200, deepcopy(PRODUCT)),
        }
        FixtureHandler.hits = []
        self.config = {
            "watch": {"name": "Robin", "currency": "CAD", "threshold": 50, "cardId": "EB05-010"},
            "settings": {"requestDelaySeconds": 0, "timeoutSeconds": 2, "intervalMinutes": 30},
            "stores": [{"id": "fixture", "name": "Canadian fixture", "url": self.base, "productUrls": [self.base + "/products/robin"], "discover": True}],
        }

    def test_exact_identity_rejects_wrong_art_language_grade_card_and_bundle(self):
        self.assertTrue(exact_card(PRODUCT))
        for bad in [
            TITLE.replace("EB05-010", "OP09-062"),
            TITLE.replace("Alternate Art", "Regular Art"),
            TITLE + " Japanese", TITLE + " PSA 10", TITLE + " (SP)",
            TITLE + " Non-Foil", TITLE + " Playset", TITLE + " Manga",
        ]:
            with self.subTest(title=bad):
                self.assertFalse(exact_card({"title": bad}))
        # Do not match card words or art markers appearing only in recommendations.
        self.assertFalse(exact_card({"title": "Nico Robin EB05-010", "description": TITLE}))

    def test_price_normalization_and_invalid_cents(self):
        self.assertEqual(str(cents_price("4999")), "49.99")
        for bad in (None, True, "NaN", "Infinity", -100, 0, "49.99"):
            with self.subTest(price=bad):
                with self.assertRaises(ValueError):
                    cents_price(bad)

    def test_preorder_backorder_and_special_order_labels_are_rejected(self):
        for label in ("Preorder", "Pre-Order", "Pre Order", "Backorder", "Back-Order", "Back Order", "Special Order"):
            with self.subTest(label=label):
                self.assertFalse(exact_card({"title": TITLE + " " + label}))
                product = deepcopy(PRODUCT)
                product["variants"] = [{"id": 10, "title": "Near Mint " + label, "price": 4900, "available": True}]
                offers = offers_from_product(self.config["stores"][0], self.base, product, "CAD", NOW)
                self.assertEqual(offers, [])
        # A generic store footer in a product description cannot establish that
        # this particular listing is a preorder.
        self.assertTrue(exact_card({"title": TITLE, "description": "Contact us about preorders"}))

    def test_known_zero_stock_sell_through_is_rejected_but_missing_quantity_is_not(self):
        for quantity in (0, -2, "0"):
            with self.subTest(quantity=quantity):
                product = deepcopy(PRODUCT)
                product["variants"] = [{"id": 10, "title": "Near Mint", "price": 4900, "available": True, "inventory_policy": "continue", "inventory_quantity": quantity}]
                self.assertEqual(offers_from_product(self.config["stores"][0], self.base, product, "CAD", NOW), [])
        product = deepcopy(PRODUCT)
        product["variants"][0]["inventory_policy"] = "continue"
        offers = offers_from_product(self.config["stores"][0], self.base, product, "CAD", NOW)
        self.assertTrue(offers[0]["inStock"])

    def test_stock_price_and_condition_are_same_variant(self):
        product = deepcopy(PRODUCT)
        product["variants"] += [
            {"id": 12, "title": "Japanese Near Mint", "price": 2000, "available": True},
            {"id": 13, "title": "Near Mint", "price": 1000, "available": "true"},
            {"id": 14, "title": "SP Special Art", "price": 2000, "available": True},
            {"id": 15, "title": "JP Near Mint", "price": 1000, "available": True},
        ]
        offers = offers_from_product(self.config["stores"][0], self.base + "/products/robin", product, "CAD", NOW)
        self.assertEqual(len(offers), 2)
        self.assertEqual((offers[0]["price"], offers[0]["inStock"]), (49, True))
        self.assertEqual((offers[1]["price"], offers[1]["inStock"]), (35, False))
        self.assertEqual(offers_from_product(self.config["stores"][0], self.base, product, "USD", NOW), [])

    def test_actual_http_discovery_currency_and_direct_url_deduplication(self):
        result = run(self.config, now=NOW)
        self.assertEqual(result["meta"]["successfulStores"], 1)
        self.assertEqual(result["meta"]["matchingOffers"], 1)
        self.assertEqual(result["stores"][0]["status"], "ok")
        self.assertEqual(len(result["alerts"]), 1)
        self.assertEqual(result["alerts"][0]["price"], 49)
        self.assertEqual(FixtureHandler.hits.count("/products/robin.js"), 1)
        self.assertNotIn("/products/regular.js", FixtureHandler.hits)
        self.assertEqual(result["meta"]["intervalMinutes"], 30)

    def test_strict_below_threshold_excludes_fifty_dollars(self):
        FixtureHandler.routes["/products/robin.js"][1]["variants"][0]["price"] = 5000
        result = run(self.config, now=NOW)
        self.assertEqual(result["meta"]["matchingOffers"], 0)
        self.assertEqual(result["alerts"], [])

    def test_price_history_deduplication_and_new_lower_price_alert(self):
        first = run(self.config, now=NOW)
        second = run(self.config, first, now=LATER)
        self.assertEqual(len(second["alerts"]), 1)
        self.assertEqual(len(second["offers"][0]["history"]), 2)
        FixtureHandler.routes["/products/robin.js"][1]["variants"][0]["price"] = 4500
        third = run(self.config, second, now="2026-11-14T16:00:00+00:00")
        offer = next(o for o in third["offers"] if o["inStock"])
        self.assertEqual((offer["price"], offer["previousPrice"], offer["minPrice"], offer["dropAmount"]), (45, 49, 45, 4))
        self.assertEqual(third["alerts"][0]["type"], "price_drop")
        self.assertEqual(len(third["alerts"]), 2)

    def test_out_of_stock_to_in_stock_alerts_once(self):
        product = FixtureHandler.routes["/products/robin.js"][1]
        product["variants"][0]["available"] = False
        first = run(self.config, now=NOW)
        self.assertEqual(first["alerts"], [])
        product["variants"][0]["available"] = True
        second = run(self.config, first, now=LATER)
        self.assertEqual(len(second["alerts"]), 1)
        self.assertEqual(second["alerts"][0]["type"], "below_threshold")

    def test_blocked_store_retains_history_but_never_claims_current_offer(self):
        first = run(self.config, now=NOW)
        FixtureHandler.routes["/cart.js"] = (403, {})
        second = run(self.config, first, now=LATER)
        self.assertEqual(second["stores"][0]["status"], "blocked")
        self.assertEqual(second["meta"]["successfulStores"], 0)
        self.assertEqual(second["meta"]["matchingOffers"], 0)
        self.assertTrue(all(o["stale"] and not o["eligible"] and not o["belowThreshold"] for o in second["offers"]))
        self.assertEqual(len(second["alerts"]), 1)
        FixtureHandler.routes["/cart.js"] = (200, {"currency": "CAD"})
        recovered = run(self.config, second, now="2026-11-14T16:00:00+00:00")
        self.assertEqual(len(recovered["alerts"]), 1)

    def test_cad_must_be_confirmed_not_assumed_from_store(self):
        FixtureHandler.routes["/cart.js"] = (200, {"currency": "USD"})
        result = run(self.config, now=NOW)
        self.assertEqual(result["stores"][0]["status"], "error")
        self.assertEqual(result["offers"], [])
        self.assertEqual(result["alerts"], [])
        self.assertNotIn("/products/robin.js", FixtureHandler.hits)

    def test_product_currency_disagreement_is_not_used(self):
        FixtureHandler.routes["/products/robin.js"][1]["currency"] = "USD"
        result = run(self.config, now=NOW)
        self.assertEqual(result["offers"], [])
        self.assertEqual(result["stores"][0]["status"], "error")

    def test_no_match_does_not_mean_sold_out(self):
        FixtureHandler.routes["/products/robin.js"][1]["title"] = "Nico Robin EB05-010 Regular Art"
        result = run(self.config, now=NOW)
        self.assertEqual(result["stores"][0]["status"], "no_match")
        self.assertEqual(result["offers"], [])

    def test_cli_writes_current_run_to_requested_temporary_output(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "watch.json"
            output = Path(folder) / "prices.json"
            config.write_text(json.dumps(self.config))
            result = subprocess.run([sys.executable, "-B", str(Path(__file__).with_name("price_monitor.py")), "--config", str(config), "--output", str(output)], capture_output=True, text=True, check=True)
            self.assertIn("1/1 stores checked; 1 current in-stock offers below CA$50", result.stdout)
            saved = json.loads(output.read_text())
            self.assertEqual(saved["meta"]["matchingOffers"], 1)
            self.assertTrue(saved["meta"]["lastChecked"])
            self.assertFalse(output.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
