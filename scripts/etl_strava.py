from pathlib import Path
import time
import requests
import yaml
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from scripts.db import get_conn, init_db, upsert_events

AUTH_URL = "https://www.strava.com/oauth/token"
API_BASE = "https://www.strava.com/api/v3"


def get_access_token():
    load_dotenv()
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")
    refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
    if not all([client_id, client_secret, refresh_token]):
        raise RuntimeError("Missing STRAVA credentials in .env")
    r = requests.post(
        AUTH_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_activities(limit: int, token: str):
    page = 1
    per_page = min(200, limit)
    fetched = []
    while len(fetched) < limit:
        r = requests.get(
            f"{API_BASE}/athlete/activities",
            headers={"Authorization": f"Bearer {token}"},
            params={"page": page, "per_page": per_page},
            timeout=30,
        )
        r.raise_for_status()
        items = r.json()
        if not items:
            break
        fetched.extend(items)
        page += 1
        time.sleep(0.2)
    return fetched[:limit]


def download_gpx(activity_id: int, token: str, out_dir: Path) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    gpx_path = out_dir / f"{activity_id}.gpx"
    if gpx_path.exists():
        return gpx_path
    r = requests.get(
        f"{API_BASE}/activities/{activity_id}/streams?keys=latlng&key_by_type=true",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    # Build a minimal GPX from latlng stream if present
    latlng = data.get("latlng", {}).get("data")
    if not latlng:
        return None
    from xml.etree.ElementTree import Element, SubElement, ElementTree
    gpx = Element("gpx", attrib={"version": "1.1", "creator": "personal_timeline"})
    trk = SubElement(gpx, "trk"); trkseg = SubElement(trk, "trkseg")
    for lat, lon in latlng:
        trkpt = SubElement(trkseg, "trkpt", attrib={"lat": str(lat), "lon": str(lon)})
    ElementTree(gpx).write(gpx_path, encoding="utf-8", xml_declaration=True)
    return gpx_path


def run(config_path: str = "config.yaml", fetch: bool = True):
    cfg = yaml.safe_load(Path(config_path).read_text())
    if not cfg.get("strava", {}).get("enabled", True):
        print("[strava] disabled in config")
        return
    db_path = Path(cfg["paths"]["db_path"])
    gpx_dir = Path(cfg["paths"]["strava_gpx_dir"])
    limit = int(cfg["strava"].get("fetch_limit", 200))

    conn = get_conn(db_path)
    init_db(conn)

    token = get_access_token()
    acts = fetch_activities(limit, token)

    rows = []
    for a in acts:
        try:
            aid = a["id"]
            name = a.get("name", "Activity")
            start = datetime.fromisoformat(a["start_date"][:-1]).replace(tzinfo=timezone.utc)
            lat = a.get("start_latlng", [None, None])[0]
            lon = a.get("start_latlng", [None, None])[1]
            subtype = a.get("type", "Workout")
            gpx_path = download_gpx(aid, token, gpx_dir)
            rows.append((
                "strava", subtype.lower(), start.isoformat(), start.date().isoformat(),
                lat, lon, str(gpx_path) if gpx_path else None, name, None, str(aid)
            ))
        except Exception as e:
            print(f"[strava] skip {a.get('id')}: {e}")

    if rows:
        upsert_events(conn, rows)
        print(f"[strava] upserted {len(rows)} events")
    else:
        print("[strava] no activities found")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args()
    run(fetch=not args.no_fetch)
