from pathlib import Path
import pandas as pd
from datetime import datetime, timezone
import yaml
from scripts.db import get_conn, init_db, upsert_events


def run(config_path: str = "config.yaml"):
    cfg = yaml.safe_load(Path(config_path).read_text())
    notes_csv = Path(cfg["paths"]["notes_csv"])
    db_path = Path(cfg["paths"]["db_path"])

    conn = get_conn(db_path)
    init_db(conn)

    if not notes_csv.exists():
        print("[notes] notes.csv not found; skipping")
        return

    df = pd.read_csv(notes_csv)
    # optional time column support
    def parse_ts(row):
        date = str(row.get("date"))
        t = str(row.get("time")) if "time" in row and not pd.isna(row.get("time")) else "12:00"
        dt = datetime.fromisoformat(f"{date} {t}")
        return dt.replace(tzinfo=timezone.utc)

    rows = []
    for _, r in df.iterrows():
        try:
            dt = parse_ts(r)
            day = dt.date().isoformat()
            lat = r.get("lat"); lon = r.get("lon")
            title = str(r.get("title", "Note"))
            text = str(r.get("text", ""))
            rows.append(("note", None, dt.isoformat(), day, lat, lon, None, title, text, title + day))
        except Exception as e:
            print(f"[notes] skip row due to {e}")

    if rows:
        upsert_events(conn, rows)
        print(f"[notes] upserted {len(rows)} events")
    else:
        print("[notes] no rows to ingest")

if __name__ == "__main__":
    run()