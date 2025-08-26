```md
# Personal Timeline + Map (Free, Local‑First)

A lightweight, free, local-first "Day One" alternative built with Python. It auto-aggregates:

- **Photos** (timestamp + GPS) from a synced folder (Google Photos/Drive)
- **Strava workouts** (GPX + stats) via Strava API
- **Manual notes/places** from a simple CSV

Then generates a searchable **daily timeline** with an **interactive map**. On the map, you can:

- See **photo pins**, **place pins**, and **workout routes**
- Toggle **dotted connectors** between sequential locations
- Show **actual GPX tracks** for routes (routes layer can replace connectors)

All output is static HTML (Folium/Leaflet) saved to `data/dashboard/`, so you can open it from your phone or computer via any synced drive.

## Quick Start

1. **Install**

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

2. **Configure** `config.yaml` and (optionally) `.env` for Strava credentials.

3. **Sync data**
   - Point your Google Photos/Drive to `data/photos/` (or periodically drop exports).
   - Run `python scripts/etl_strava.py --fetch` once to pull recent Strava activities.
   - Put quick notes in `data/notes.csv` (see example inside).

4. **Build dashboard**

```bash
python scripts/build_dashboard.py
```

Open `data/dashboard/index.html` in your browser.

5. **Auto-update (optional)**

Run the watcher to ingest new files and regenerate the dashboard on change:

```bash
python scripts/run_watcher.py
```

## Strava API Setup (brief)
- Create an app at https://www.strava.com/settings/api
- Put `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REFRESH_TOKEN` into `.env`
- First run of `etl_strava.py --fetch` will exchange for an access token and download your recent activities + GPX files.

## Notes CSV Format
`data/notes.csv` (header required):

```csv
date,title,lat,lon,text
2025-08-25,Dinner @ Sushi Place,49.2827,-123.1207,Great nigiri with friends
```

`lat/lon` are optional (blank = no pin). You can also add `time` as `HH:MM` (24h) in an optional column.

## Privacy
Everything lives locally. No servers, no subscriptions. You can keep the folder inside iCloud/Google Drive/Dropbox/Syncthing if you want multi-device access.
```