from pathlib import Path
import time
import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from scripts.etl_photos import run as photos_run
from scripts.etl_strava import run as strava_run
from scripts.etl_notes import run as notes_run
from scripts.build_dashboard import run as build_run

class Handler(FileSystemEventHandler):
    def __init__(self, cfg):
        self.cfg = cfg
        self.last_run = 0
        self.cooldown = 5  # seconds to debounce

    def on_any_event(self, event):
        now = time.time()
        if now - self.last_run < self.cooldown:
            return
        self.last_run = now
        print("[watcher] change detected; updating…")
        try:
            photos_run()
        except Exception as e:
            print("[watcher] photos etl failed:", e)
        try:
            notes_run()
        except Exception as e:
            print("[watcher] notes etl failed:", e)
        try:
            strava_run()
        except Exception as e:
            print("[watcher] strava etl failed:", e)
        try:
            build_run()
        except Exception as e:
            print("[watcher] build dashboard failed:", e)


def run(config_path: str = "config.yaml"):
    cfg = yaml.safe_load(Path(config_path).read_text())
    paths = [
        Path(cfg["paths"]["photos_dir"]),
        Path(cfg["paths"]["strava_gpx_dir"]),
        Path(cfg["paths"]["notes_csv"]).parent,
    ]
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)

    event_handler = Handler(cfg)
    observer = Observer()
    for p in paths:
        observer.schedule(event_handler, str(p), recursive=True)

    print("[watcher] watching:")
    for p in paths:
        print(" -", p.resolve())
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    run()
