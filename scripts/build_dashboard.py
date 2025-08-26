from pathlib import Path
import folium
import sqlite3
import yaml
from scripts.timeline_utils import group_by_day, pairwise_connectors
from scripts.gpx_utils import gpx_to_polyline, simplify

HTML_INDEX_HEAD = """
<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Timeline Dashboard</title>
<style>body{font-family:system-ui, -apple-system, Segoe UI, Roboto, sans-serif;margin:20px;}a{color:#2563eb;text-decoration:none}a:hover{text-decoration:underline} .day{margin-bottom:6px}</style>
</head><body>
<h1>Timeline</h1>
<p>Select a day to view the map & entries.</p>
<ul>
"""
HTML_INDEX_TAIL = """
</ul></body></html>
"""


def fetch_all(conn: sqlite3.Connection):
    cur = conn.execute("SELECT id, source, subtype, ts_utc, day, lat, lon, path, title, text, ext_id FROM events ORDER BY ts_utc")
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return rows


def build_day_map(day: str, events, cfg, out_dir: Path):
    center = [cfg["map"]["center_lat"], cfg["map"]["center_lon"]]
    m = folium.Map(location=center, zoom_start=cfg["map"]["zoom_start"]) 

    photos_fg = folium.FeatureGroup(name="Photos", show=True)
    notes_fg = folium.FeatureGroup(name="Notes/Places", show=True)
    routes_fg = folium.FeatureGroup(name="Routes (GPX)", show=True)
    connectors_fg = folium.FeatureGroup(name="Connectors (dotted)", show=True)

    # Markers
    for e in events:
        if e["lat"] is None or e["lon"] is None:
            continue
        popup = f"<b>{e.get('title') or e['source'].title()}</b><br>{e['ts_utc']}"
        if e["source"] == "photo":
            folium.Marker([e["lat"], e["lon"]], popup=popup, icon=folium.Icon(icon="camera")).add_to(photos_fg)
        elif e["source"] == "strava":
            folium.Marker([e["lat"], e["lon"]], popup=popup, icon=folium.Icon(icon="flag")).add_to(routes_fg)
        else:
            folium.Marker([e["lat"], e["lon"]], popup=popup).add_to(notes_fg)

    # Dotted connectors between sequential geolocated events
    pairs = pairwise_connectors([type("E", (), r) for r in events])
    for a,b in pairs:
        folium.PolyLine(
            locations=[[a.lat, a.lon],[b.lat, b.lon]],
            weight=cfg["map"]["connector_weight"],
            dash_array=cfg["map"]["connector_dash"],
        ).add_to(connectors_fg)

    # GPX routes (if any) — drawn as solid lines; visually "replace" connectors
    for e in events:
        if e["source"] == "strava" and e.get("path"):
            pts = simplify(gpx_to_polyline(Path(e["path"])) or [], 0.0003)
            if len(pts) >= 2:
                folium.PolyLine(locations=pts, weight=cfg["map"]["route_weight"]).add_to(routes_fg)

    photos_fg.add_to(m)
    notes_fg.add_to(m)
    routes_fg.add_to(m)
    connectors_fg.add_to(m)
    folium.LayerControl().add_to(m)

    out_path = out_dir / f"{day}.html"
    m.save(str(out_path))
    return out_path


def run(config_path: str = "config.yaml"):
    cfg = yaml.safe_load(Path(config_path).read_text())
    db_path = Path(cfg["paths"]["db_path"])
    out_dir = Path(cfg["paths"]["dashboard_dir"]) 
    out_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    rows = fetch_all(conn)
    days = group_by_day(rows)

    index_items = []
    for day, events in sorted(days.items()):
        html_path = build_day_map(day, [e.__dict__ if hasattr(e, "__dict__") else e for e in events], cfg, out_dir)
        index_items.append(f"<li class='day'><a href='{html_path.name}'>{day}</a> — {len(events)} entries</li>")

    (out_dir / "index.html").write_text(HTML_INDEX_HEAD + "\n".join(index_items) + HTML_INDEX_TAIL, encoding="utf-8")
    print(f"[dashboard] wrote {len(index_items)} day pages -> {out_dir/'index.html'}")

if __name__ == "__main__":
    run()
