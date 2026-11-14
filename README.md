# Robin Price Drop Watchlist

Watches **Nico Robin EB05-010 alternate-art foil**, starting with [Enter the Battlefield's exact listing](https://enterthebattlefield.ca/products/nico-robin-010-alternate-art-eb05-010-extra-booster-one-piece-heroines-edition-vol-2-foil), plus a bounded selection of Canadian card retailers. The target is a matching, in-stock variant **strictly below CA$50 before shipping and tax**. CA$50 itself does not qualify.

## What the watchlist does

- Checks configured public retailer endpoints approximately every 30 minutes using GitHub Actions. GitHub can delay scheduled jobs; this is not continuous or instant monitoring.
- Confirms card identity, variant availability and CAD currency before treating a price as a match. Regular-art cards, other card numbers, graded cards and explicitly foreign-language listings are excluded.
- Keeps bounded per-variant price history. First sightings under target are labelled as under-target discoveries; actual price drops require an earlier observed price.
- Separates failed/blocked checks from out-of-stock cards and no matching listing. Old observations are marked stale and cannot qualify as current deals.
- Publishes the latest result to a phone-friendly dashboard. Offline data is explicitly stale.

This is a configured retailer watchlist, not an exhaustive search of every Canadian seller. Search APIs may omit products; access controls and site changes can prevent checks. An observed offer does not reserve a card, and shipping/tax are not included. Different raw-card conditions are shown separately; no minimum condition was specified.

## Notifications

**Push and email delivery are not configured.** Scheduled checks and dashboard updates work independently of notification delivery. The notifications page states this explicitly. The old ticket-alert sender is not run by the Robin workflow. A future notification setup needs the user's chosen service and explicit subscription; do not broadcast Robin alerts to legacy ticket subscribers.

## Development

Use Python 3.12, matching CI. From the repository root:

```sh
python3 -m venv /workspace/.venvs/op18-ticket-radar
/workspace/.venvs/op18-ticket-radar/bin/python -m pip install -r requirements.txt
/workspace/.venvs/op18-ticket-radar/bin/python -m unittest discover -s scripts -p 'test_price_monitor.py' -v
/workspace/.venvs/op18-ticket-radar/bin/python -m http.server 8000 --bind 127.0.0.1
```

The static site has no build or database. Use localhost internally when testing the service worker. It caches the shell but never treats a cached price feed as live. A browser refresh retrieves the latest *published* scan; it does not trigger a shop scan.

The public checker is `scripts/price_monitor.py`, configured by `data/watchlist.json`; its output is `data/prices.json`. Running it normally updates the tracked feed. Use its CLI output override when experimenting to preserve the feed. Keep normal TLS verification enabled. Check public sites considerately; do not bypass login or anti-bot protections.

The earlier OP-18 ticket-scanner files remain as an archive. The active workflow and home page now serve the Robin price watchlist.

## Hosting

`.github/workflows/monitor.yml` tests the scanner, fetches current offers, commits the feed/history and deploys the dashboard to GitHub Pages. Run it manually with **Actions → Robin price-drop watchlist → Run workflow**. GitHub Pages must use **GitHub Actions** as its deployment source. The workflow requires repository contents and Pages write permissions, declared in the workflow.

The environment display name is separate from the GitHub repository name and Pages URL. Renaming a repository requires GitHub administration permission; do not assume a new Pages URL exists until GitHub confirms it and deployment succeeds.
