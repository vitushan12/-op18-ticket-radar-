#!/usr/bin/env python3
"""Conservative, read-only Canadian Nico Robin price watcher.

Shopify product AJAX prices are cents in the session's presentment currency.
We verify that currency using cart.js in the same Session before using a price.
No cart additions, customer login, purchases, or anti-bot bypasses are performed.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlparse, urlunparse

import requests

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data/watchlist.json"
OUTPUT = ROOT / "data/prices.json"
UA = "RobinPriceWatch/1.0 (public Canadian card listing monitor; no purchases)"
CARD = re.compile(r"(?<![a-z0-9])eb\s*0?5\s*[-–]?\s*0?10(?![a-z0-9])", re.I)
ALT = re.compile(r"\b(?:alternate\s*art|alt\.?\s*art|parallel(?:\s*art)?)\b", re.I)
WRONG = re.compile(r"\b(?:japanese|japan|jp|jpn|chinese|korean|french|german|italian|spanish|psa|bgs|cgc|graded|slab|manga|proxy|replica|custom|playset|bundle|sealed|booster\s*(?:box|pack|case))\b", re.I)
NONFOIL = re.compile(r"\bnon[-\s]?foil\b", re.I)
REGULAR = re.compile(r"\b(?:regular|normal|standard|base)\s*(?:art|version)\b", re.I)
SPECIAL = re.compile(r"\b(?:sp|special\s+(?:art|rare)|anniversary|treasure\s+rare)\b", re.I)
NONSTOCK = re.compile(r"\b(?:pre[-\s]?order|back[-\s]?order|special[-\s]?order)\b", re.I)


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def text(value):
    if isinstance(value, (list, tuple)):
        return " ".join(map(str, value))
    return str(value or "")


def exact_card(product):
    """Match identity from title, not unrelated recommendations or descriptions.

    English is the configured Canadian English catalogue default unless a title
    explicitly identifies another language. Alternate art is inherently foil for
    this card; explicitly nonfoil/graded/special-art listings are rejected.
    """
    title = text(product.get("title"))
    normalized = re.sub(r"[^a-z0-9]+", " ", title.lower())
    return bool(
        re.search(r"\bnico\s+robin\b", normalized)
        and CARD.search(title)
        and ALT.search(title)
        and not WRONG.search(title)
        and not NONFOIL.search(title)
        and not REGULAR.search(title)
        and not SPECIAL.search(title)
        and not NONSTOCK.search(title)
    )


def variant_ok(variant):
    label = " ".join(text(variant.get(k)) for k in ("title", "option1", "option2", "option3"))
    if WRONG.search(label) or NONFOIL.search(label) or REGULAR.search(label) or SPECIAL.search(label) or NONSTOCK.search(label):
        return False
    # Some catalogues combine art/language variants under a matching title.
    if re.search(r"\b(?:regular|normal|standard|base|nonfoil|non-foil)\b", label, re.I):
        return False
    # Shopify can accept an order after physical stock reaches zero. When the
    # public response explicitly exposes that situation it is not an in-stock
    # offer, even though the generic available flag remains true. Most AJAX
    # responses omit quantity; absence alone is not evidence of a backorder.
    if variant.get("inventory_policy") == "continue" and variant.get("inventory_quantity") is not None:
        try:
            quantity = Decimal(str(variant["inventory_quantity"]))
        except InvalidOperation:
            quantity = None
        if quantity is not None and quantity.is_finite() and quantity <= 0:
            return False
    return True


def cents_price(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("Missing or invalid variant price")
    try:
        cents = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("Invalid variant price") from error
    if not cents.is_finite() or cents <= 0 or cents != cents.to_integral_value():
        raise ValueError("Product AJAX price must be positive integer cents; free placeholders are unverified")
    return (cents / Decimal(100)).quantize(Decimal("0.01"))


def product_url(url, base):
    parsed = urlparse(urljoin(base, url))
    origin = urlparse(base)
    if parsed.scheme not in ("https", "http") or parsed.netloc.lower() != origin.netloc.lower():
        return None
    match = re.search(r"/products/([^/]+)", parsed.path)
    if not match:
        return None
    handle = re.sub(r"\.(?:js|json)$", "", match.group(1))
    return urlunparse((parsed.scheme, parsed.netloc, "/products/" + handle, "", "", ""))


class StoreClient:
    def __init__(self, base, timeout=12, delay=0.35, session=None):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.delay = delay
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept": "application/json"})
        self.last_request = 0.0
        self.requests = 0

    def get_json(self, url, params=None):
        pause = self.delay - (time.monotonic() - self.last_request)
        if pause > 0:
            time.sleep(pause)
        self.last_request = time.monotonic()
        self.requests += 1
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        # Shopify stores may redirect to their canonical domain; redirect results
        # remain TLS-verified and no authentication is supplied to third parties.
        return response.json()

    def currency(self):
        cart = self.get_json(self.base + "/cart.js", {"currency": "CAD"})
        value = text(cart.get("currency")).upper()
        if value != "CAD":
            raise ValueError("CAD presentment currency could not be confirmed")
        return value

    def discover(self, limit=6):
        result = self.get_json(self.base + "/search/suggest.json", {
            "q": "EB05-010",
            "resources[type]": "product",
            "resources[limit]": min(limit, 10),
            "resources[options][unavailable_products]": "last",
        })
        products = result.get("resources", {}).get("results", {}).get("products", [])
        urls = []
        for candidate in products:
            if not isinstance(candidate, dict) or not exact_card(candidate):
                continue
            url = product_url(candidate.get("url", ""), self.base)
            if url and url not in urls:
                urls.append(url)
        return urls[:limit]

    def product(self, url):
        result = self.get_json(url + ".js", {"currency": "CAD"})
        if not isinstance(result, dict) or not isinstance(result.get("variants"), list):
            raise ValueError("Product endpoint returned unexpected data")
        if result.get("currency") and text(result["currency"]).upper() != "CAD":
            raise ValueError("Product response currency differs from CAD session")
        return result


def offer_id(store_id, url, variant):
    return hashlib.sha256(f"{store_id}|{url}|{variant.get('id', variant.get('title', ''))}".encode()).hexdigest()[:20]


def offers_from_product(store, url, product, currency, now):
    if currency != "CAD" or not exact_card(product):
        return []
    offers = []
    for variant in product["variants"]:
        if not isinstance(variant, dict) or not variant_ok(variant):
            continue
        # An explicit boolean is essential; strings and aggregate product stock
        # cannot establish that this particular priced variant can be bought.
        if variant.get("available") not in (True, False) or not isinstance(variant.get("available"), bool):
            continue
        price = cents_price(variant.get("price"))
        label = text(variant.get("title")) or "Default variant"
        variant_url = url + ("?variant=" + str(variant["id"]) if variant.get("id") else "")
        offers.append({
            "id": offer_id(store["id"], url, variant),
            "storeId": store["id"],
            "title": text(product.get("title")),
            "variant": label,
            "condition": label,
            "url": variant_url,
            "currency": "CAD",
            "price": float(price),
            "inStock": variant["available"],
            "firstSeen": now,
            "lastSeen": now,
            "stale": False,
            "image": product.get("featured_image") or None,
        })
    return offers


def update_offer(current, previous, threshold, now):
    result = deepcopy(current)
    result["eligible"] = current["inStock"] and not current["stale"]
    result["belowThreshold"] = result["eligible"] and Decimal(str(current["price"])) < threshold
    result["previousPrice"] = previous.get("price") if previous else None
    result["firstSeen"] = previous.get("firstSeen", now) if previous else now
    result["minPrice"] = min(current["price"], previous.get("minPrice", previous["price"])) if previous else current["price"]
    result["changed"] = bool(previous and (current["price"], current["inStock"]) != (previous["price"], previous["inStock"]))
    result["dropAmount"] = round(previous["price"] - current["price"], 2) if previous and current["price"] < previous["price"] else None
    history = deepcopy(previous.get("history", [])) if previous else []
    point = {"checkedAt": now, "price": current["price"], "inStock": current["inStock"]}
    # Capture every actual observation, with a bounded history and no extra
    # points for rerunning an identical timestamp (e.g. a workflow retry).
    if not history or history[-1] != point:
        history.append(point)
    result["history"] = history[-96:]
    alert = None
    was_below = bool(previous and previous.get("inStock") and Decimal(str(previous["price"])) < threshold)
    if result["belowThreshold"] and (not was_below or result["dropAmount"]):
        type_ = "price_drop" if was_below and result["dropAmount"] else "below_threshold"
        alert_key = f"{current['id']}|{type_}|{current['price']}|{now}"
        alert = {
            "id": hashlib.sha256(alert_key.encode()).hexdigest()[:20],
            "offerId": current["id"], "storeId": current["storeId"],
            "type": type_, "price": current["price"],
            "previousPrice": result["previousPrice"], "createdAt": now,
            "url": current["url"],
            "message": f"Nico Robin EB05-010 alternate art in stock for CA${current['price']:.2f} before shipping/tax ({current['variant']}).",
        }
    return result, alert


def check_store(store, settings, now, client_factory=StoreClient):
    summary = {k: store[k] for k in ("id", "name", "url")}
    summary.update({"checkedAt": now, "status": "error", "message": "Check incomplete", "offers": []})
    offers = []
    client = client_factory(store["url"], timeout=settings.get("timeoutSeconds", 12), delay=settings.get("requestDelaySeconds", 0.35))
    errors = []
    try:
        currency = client.currency()
        urls = []
        for candidate in store.get("productUrls", []):
            url = product_url(candidate, store["url"])
            if url and url not in urls:
                urls.append(url)
        if store.get("discover", True):
            try:
                for url in client.discover(settings.get("maxDiscoveryProducts", 6)):
                    if url not in urls:
                        urls.append(url)
            except (requests.RequestException, ValueError, TypeError, KeyError):
                errors.append("Product discovery unavailable")
        limit = min(settings.get("maxProductsPerStore", 6), 10)
        for url in urls[:limit]:
            try:
                product = client.product(url)
                offers.extend(offers_from_product(store, url, product, currency, now))
            except (requests.RequestException, ValueError, TypeError, KeyError):
                errors.append("A product could not be verified")
        # Deduplicate direct URLs also returned by suggest and variant IDs.
        offers = list({offer["id"]: offer for offer in offers}.values())
        summary["offers"] = [offer["id"] for offer in offers]
        if offers:
            summary.update(status="ok", message=f"CAD and exact card variants verified ({len(offers)} variant(s))" + ("; " + "; ".join(errors) if errors else ""))
        elif errors:
            summary.update(status="error", message="; ".join(dict.fromkeys(errors)) + "; no current offer verified")
        else:
            summary.update(status="no_match", message="No exact alternate-art EB05-010 listing found in bounded search")
    except requests.HTTPError as error:
        code = error.response.status_code if error.response is not None else None
        summary.update(status="blocked" if code in (401, 403, 429) else "error", message=f"Public store check unavailable (HTTP {code}); price/stock unverified")
    except (requests.RequestException, ValueError, TypeError, KeyError) as error:
        # Do not expose response bodies, cookies, proxy details or credentials.
        summary.update(status="error", message=f"Public store check unavailable ({type(error).__name__}); CAD price/stock unverified")
    summary["requests"] = client.requests
    return summary, offers


def run(config, previous=None, now=None, client_factory=StoreClient):
    now = now or utc_now()
    previous = previous or {}
    watch = deepcopy(config["watch"])
    threshold = Decimal(str(watch["threshold"]))
    if watch.get("currency") != "CAD" or threshold != Decimal("50"):
        raise ValueError("This watch requires strict under-CA$50 pricing")
    existing = {offer["id"]: offer for offer in previous.get("offers", [])}
    offers = {}
    stores = []
    alerts = deepcopy(previous.get("alerts", []))
    alert_ids = {alert["id"] for alert in alerts}
    settings = config.get("settings", {})
    for store in config["stores"]:
        summary, found = check_store(store, settings, now, client_factory)
        stores.append(summary)
        for current in found:
            offer, alert = update_offer(current, existing.get(current["id"]), threshold, now)
            offers[offer["id"]] = offer
            if alert and alert["id"] not in alert_ids:
                alerts.insert(0, alert)
                alert_ids.add(alert["id"])
    active_stores = {store["id"] for store in config["stores"]}
    for id_, old in existing.items():
        if id_ not in offers and old["storeId"] in active_stores:
            stale = deepcopy(old)
            stale.update(stale=True, eligible=False, belowThreshold=False, changed=False, dropAmount=None)
            offers[id_] = stale
    offer_list = sorted(offers.values(), key=lambda o: (o["stale"], not o["inStock"], o["price"], o["storeId"]))
    return {
        "schemaVersion": 1,
        "watch": watch,
        "meta": {
            "lastChecked": now,
            "successfulStores": sum(store["status"] in ("ok", "no_match") for store in stores),
            "totalStores": len(stores),
            "matchingOffers": sum(offer["belowThreshold"] for offer in offer_list),
            "intervalMinutes": settings.get("intervalMinutes", 30),
            "currencyVerified": "Shopify cart.js presentment currency in same session",
            "priceIncludesShippingTax": False,
        },
        "stores": stores,
        "offers": offer_list,
        "alerts": alerts[:80],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    previous = json.loads(args.output.read_text()) if args.output.exists() else None
    result = run(config, previous)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement prevents serving a partially written JSON feed.
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(args.output)
    meta = result["meta"]
    print(f"Robin price check: {meta['successfulStores']}/{meta['totalStores']} stores checked; {meta['matchingOffers']} current in-stock offers below CA$50; checkedAt={meta['lastChecked']}")
    for store in result["stores"]:
        print(f"{store['name']}: {store['status']} — {store['message']}")


if __name__ == "__main__":
    main()
