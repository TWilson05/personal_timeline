from pathlib import Path
from datetime import datetime, timezone
import exifread
from PIL import Image
from scripts.db import get_conn, init_db, upsert_events
import pandas as pd
import yaml

# Simple EXIF helpers

def _dms_to_deg(dms, ref):
    deg = float(dms[0].num) / dms[0].den
    minutes = float(dms[1].num) / dms[1].den
    seconds = float(dms[2].num) / dms[2].den
    sign = -1 if ref in ["S", "W"] else 1
    return sign * (deg + minutes/60 + seconds/3600)


def extract_exif_latlon_ts(photo_path: Path):
    with open(photo_path, 'rb') as f:
        tags = exifread.process_file(f, details=False)
    # Timestamp
    ts = None
    for key in ("EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"):
        if key in tags:
            ts = str(tags[key])
            break
    if ts:
        # EXIF format: "YYYY:MM:DD HH:MM:SS"
        dt = datetime.strptime(ts, "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
    else:
        # Fallback to file mtime
        dt = datetime.fromtimestamp(photo_path.stat().st_mtime, tz=timezone.utc)

    # GPS
    lat = lon = None
    if "GPS GPSLatitude" in tags and "GPS GPSLongitude" in tags:
        lat = _dms_to_deg(tags["GPS GPSLatitude"].values, str(tags.get("GPS GPSLatitudeRef", "N")))
        lon = _dms_to_deg(tags["GPS GPSLongitude"].values, str(tags.get("GPS GPSLongitudeRef", "E")))
    return dt, lat, lon


def run(config_path: str = "config.yaml"):
    cfg = yaml.safe_load(Path(config_path).read_text())
    photos_dir = Path(cfg["paths"]["photos_dir"])
    db_path = Path(cfg["paths"]["db_path"])

    conn = get_conn(db_path)
    init_db(conn)

    rows = []
    exts = {".jpg", ".jpeg", ".png", ".heic", ".JPG", ".JPEG", ".PNG", ".HEIC"}

    for p in photos_dir.rglob("*"):
        if not p.suffix in exts or not p.is_file():
            continue
        try:
            dt, lat, lon = extract_exif_latlon_ts(p)
            day = dt.date().isoformat()
            rows.append((
                "photo", p.suffix.lower().lstrip('.'), dt.isoformat(), day, lat, lon, str(p),
                p.stem, None, str(p)  # ext_id uses path for uniqueness
            ))
        except Exception as e:
            print(f"[photos] skip {p}: {e}")

    if rows:
        upsert_events(conn, rows)
        print(f"[photos] upserted {len(rows)} events")
    else:
        print("[photos] no new photos found")

if __name__ == "__main__":
    run()
