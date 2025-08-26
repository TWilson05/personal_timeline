from pathlib import Path
import gpxpy

def gpx_to_polyline(gpx_path: Path):
    if not gpx_path or not Path(gpx_path).exists():
        return []
    pts = []
    with open(gpx_path, 'r', encoding='utf-8') as f:
        gpx = gpxpy.parse(f)
        for track in gpx.tracks:
            for seg in track.segments:
                for p in seg.points:
                    if p.latitude is not None and p.longitude is not None:
                        pts.append((p.latitude, p.longitude))
        # Also consider routes if present
        for route in gpx.routes:
            for p in route.points:
                pts.append((p.latitude, p.longitude))
    return pts

# Ramer–Douglas–Peucker simplification (optional)

def simplify(points, epsilon=0.0002):
    if len(points) < 3:
        return points

    import math

    def dist(p, a, b):
        (x0,y0),(x1,y1),(x2,y2)= (p,a,b)
        if (x1,y1)==(x2,y2):
            return math.hypot(x0-x1,y0-y1)
        t = max(0,min(1, ((x0-x1)*(x2-x1)+(y0-y1)*(y2-y1))/((x2-x1)**2+(y2-y1)**2)))
        px,py = x1 + t*(x2-x1), y1 + t*(y2-y1)
        return math.hypot(x0-px, y0-py)

    def rdp(pts):
        if len(pts) <= 2:
            return pts
        max_d, idx = 0.0, 0
        for i in range(1,len(pts)-1):
            d = dist(pts[i], pts[0], pts[-1])
            if d > max_d:
                max_d, idx = d, i
        if max_d > epsilon:
            left = rdp(pts[:idx+1])
            right = rdp(pts[idx:])
            return left[:-1] + right
        else:
            return [pts[0], pts[-1]]

    return rdp(points)
