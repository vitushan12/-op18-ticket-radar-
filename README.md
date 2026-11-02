# OP-18 Ticket Radar — iPhone app

An installable, phone-first **progress dashboard** for One Piece TCG OP-18 release-event tickets around **Toronto, Scarborough and Vaughan**. Includes 16 card shops and 13 event dates from a **November 1, 2026 research snapshot**.

## What works

- iPhone-friendly PWA, with Home / Events / Shops / Checks / More tabs.
- Date/time and price lists; area, status and store filters; direct store/ticket links.
- Star favourite shops, track personal progress (asked the store, joined restock waitlist, applied on TCG+), add private notes, mark a ticket secured, add shops and export tracking settings.
- Saves personal choices **locally on the iPhone** with browser storage.
- Displays scanner check timestamps, successful/failed store checks, and status transitions.
- Hosted workflow can scan public shop event pages for *possible new OP-18 event listings* and cautiously verify available ticket variants using public Shopify product JSON.
- Works offline for existing app screens after initial installation (but **never** assumes offline ticket data is live).

## Install on an iPhone (requires free hosting)

1. Create a **new public GitHub repository** (for example, `op18-ticket-radar`).
2. Upload **all the files and folders in this ZIP**, preserving paths, including the hidden `.github/workflows/monitor.yml` file. It is often easiest to upload from a computer. Do not upload the enclosing `OP18-Ticket-Radar` folder as an extra level.
3. In GitHub, open **Settings → Pages → Build and deployment → Deploy from a branch**. Choose **`main` / `/(root)`** and Save. Wait for GitHub to publish the HTTPS website; typically the URL is `https://YOUR-USERNAME.github.io/op18-ticket-radar/`.
4. In GitHub **Settings → Actions → General**, ensure workflows are allowed and **Workflow permissions → Read and write permissions** is selected where this option is available. The workflow also declares `contents: write`.
5. Under **Actions → Update OP-18 ticket radar → Run workflow**, run it once. The workflow also runs *approximately once an hour* via GitHub Actions; GitHub may delay or pause scheduled runs.
6. On your iPhone, open the published HTTPS link in **Safari** → tap the **Share** icon → **Add to Home Screen** → **Add**. Open **OP18 Radar** from your Home Screen.

**Without hosting and the workflow:** the app will still display the saved November 1 snapshot. Do not treat it as a live stock feed. Opening `index.html` from an unzipped iPhone Files folder cannot give reliable installation or live synchronization.

## Your existing notifications

Your separately configured **ChatGPT OP-18 GTA Ticket Watch** is already scheduled hourly. Leave ChatGPT notifications enabled on iPhone. The ChatGPT automation and this app **do not share a data/API connection**; the app does not display that automation's internal run history and does not issue background push notifications. Hosting the workflow creates a **second independent scheduled web check** for the dashboard. If a ticket is important, use both direct shop restock notifications and ChatGPT alerts.

## Scanner design & limitations

- `scripts/monitor.py` checks public event pages and appends *potential new event listing* links in `data/status.json` with status **unverified**.
- For known `/products/...` ticket links, it attempts a public Shopify `/products/slug.js` lookup and marks tickets **available** only when the ticket product and relevant variant are identifiable. Ambiguous variants are left unchanged or for manual verification.
- A **sold-out status from Nov 1** is not proof that tickets are still sold out now. Event cards display verification date and stale flags.
- Some sites use JavaScript, Cloudflare or other access controls. The scanner will show such failures without claiming stock status. It does **not** bypass anti-bot protections or log in to Bandai TCG+.
- Shop site design or event listing paths may change. New unverified listings must be manually reviewed. Adding a custom store on your phone doesn't automatically add it to the GitHub scanner; edit `data/seed.json` and `data/status.json` for the scanner to include it.
- GitHub Pages and Actions are hosted by GitHub; this ZIP does not create a live service until **you deploy it**. Background Web Push would need a separate push service and is intentionally not claimed here.
- The app does not buy tickets, hold a place, or collect payment credentials.

## Local test (computer)

```sh
python3 -m http.server 8000
```

Open `http://localhost:8000` in a browser. To test the monitor, install `requests` and run `python scripts/monitor.py`. Use the public shop sites considerately.

## Files

- `index.html`, `styles.css`, `app.js`: app UI and personal tracking.
- `manifest.webmanifest`, `sw.js`, `icons/`: installable PWA and offline shell.
- `data/seed.json`, `data/seed.js`: initial date/status snapshot.
- `data/status.json`: hosted web-check results feed.
- `scripts/monitor.py`: conservative public shop checker.
- `.github/workflows/monitor.yml`: approximately hourly GitHub Actions job.

Unofficial fan-made event tracker. Not affiliated with Bandai, One Piece, or any card shop.
