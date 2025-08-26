from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class Event:
    id: int
    source: str
    subtype: Optional[str]
    ts_utc: str
    day: str
    lat: Optional[float]
    lon: Optional[float]
    path: Optional[str]
    title: Optional[str]
    text: Optional[str]
    ext_id: Optional[str]


def pairwise_connectors(events: List[Event]):
    """Return pairs of consecutive geolocated events to be connected by dotted lines."""
    pairs = []
    last = None
    for e in events:
        if e.lat is None or e.lon is None:
            continue
        if last is not None:
            pairs.append((last, e))
        last = e
    return pairs


def group_by_day(rows: List[Dict[str, Any]]) -> Dict[str, List[Event]]:
    days: Dict[str, List[Event]] = {}
    for r in rows:
        e = Event(**r)
        days.setdefault(e.day, []).append(e)
    for k in days:
        days[k].sort(key=lambda x: x.ts_utc)
    return days
