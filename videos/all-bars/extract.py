"""Pull every bar in Wisconsin out of an OpenStreetMap extract.

usage: python3 extract.py wisconsin-latest.osm.pbf states.json out_dir

Writes:
  bars.csv / bars.json  every amenity=bar|pub|biergarten inside Wisconsin, with address
  roads.json            simplified major roads (for the basemap)
"""
import csv, json, sys, math
import osmium
import numpy as np

PBF, STATES, OUT = sys.argv[1:4]
BAR_KINDS = {"bar", "pub", "biergarten"}
ROAD_KINDS = {"motorway": 0, "trunk": 1, "primary": 2, "secondary": 3}


def point_in_polys(lon, lat, polys):
    inside = False
    for poly in polys:
        for ring in poly:
            r = np.asarray(ring)
            x, y = r[:, 0], r[:, 1]
            x2, y2 = np.roll(x, -1), np.roll(y, -1)
            cond = ((y > lat) != (y2 > lat))
            with np.errstate(divide="ignore", invalid="ignore"):
                xin = (x2 - x) * (lat - y) / (y2 - y) + x
            inside ^= bool(np.count_nonzero(cond & (lon < xin)) % 2)
    return inside


def dp(points, eps):
    """Douglas-Peucker on a list of (lon, lat)."""
    if len(points) < 3:
        return points
    a, b = np.array(points[0]), np.array(points[-1])
    pts = np.array(points)
    ab = b - a
    n = np.hypot(*ab)
    if n == 0:
        d = np.hypot(*(pts - a).T)
    else:
        d = np.abs(ab[0] * (pts[:, 1] - a[1]) - ab[1] * (pts[:, 0] - a[0])) / n
    i = int(np.argmax(d))
    if d[i] > eps:
        return dp(points[: i + 1], eps)[:-1] + dp(points[i:], eps)
    return [points[0], points[-1]]


def address(tags):
    line = " ".join(p for p in (tags.get("addr:housenumber", ""), tags.get("addr:street", "")) if p)
    city = tags.get("addr:city", "")
    tail = " ".join(p for p in ("WI", tags.get("addr:postcode", "")) if p) if (line or city) else ""
    return ", ".join(p for p in (line, city, tail) if p)


class H(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.bars, self.roads, self.places = [], [], []

    def _bar(self, kind, oid, tags, lon, lat):
        self.bars.append({
            "osm": f"{kind}/{oid}", "name": tags.get("name", ""), "type": tags.get("amenity"),
            "lat": round(lat, 6), "lon": round(lon, 6), "address": address(tags),
            "city": tags.get("addr:city", ""),
        })

    def node(self, n):
        if n.tags.get("place") in ("city", "town", "village") and "name" in n.tags:
            self.places.append((n.tags["name"], n.location.lon, n.location.lat))
        if n.tags.get("amenity") in BAR_KINDS and n.location.valid():
            self._bar("node", n.id, dict(n.tags), n.location.lon, n.location.lat)

    def way(self, w):
        amen, hw = w.tags.get("amenity"), w.tags.get("highway")
        if amen not in BAR_KINDS and hw not in ROAD_KINDS:
            return
        try:
            coords = [(nd.lon, nd.lat) for nd in w.nodes if nd.location.valid()]
        except osmium.InvalidLocationError:
            return
        if not coords:
            return
        if amen in BAR_KINDS:
            lon = sum(c[0] for c in coords) / len(coords)
            lat = sum(c[1] for c in coords) / len(coords)
            self._bar("way", w.id, dict(w.tags), lon, lat)
        else:
            simp = dp(coords, 0.0015)
            self.roads.append([ROAD_KINDS[hw], [[round(x, 4), round(y, 4)] for x, y in simp]])

    def relation(self, r):
        # a few bars are mapped as multipolygons; take the first member way's position is not available
        # without area assembly, so skip (rare).
        pass


h = H()
h.apply_file(PBF, locations=True)
wi = json.load(open(STATES))["WI"]

bars = [b for b in h.bars if point_in_polys(b["lon"], b["lat"], wi)]
# drop duplicates: same name within ~60 m (a node and a building both tagged)
bars.sort(key=lambda b: (b["name"].lower(), b["lat"]))
dedup = []
for b in bars:
    p = dedup[-1] if dedup else None
    if p and p["name"] and p["name"].lower() == b["name"].lower() and \
            math.hypot((p["lat"] - b["lat"]) * 111, (p["lon"] - b["lon"]) * 80) < 0.06:
        if not p["address"] and b["address"]:
            p["address"] = b["address"]
        continue
    dedup.append(b)

# fill in a town for bars with no addr:city, from the nearest city/town/village
P = np.array([(p[1], p[2]) for p in h.places])
for b in dedup:
    d = (P[:, 0] - b["lon"]) ** 2 * 0.53 + (P[:, 1] - b["lat"]) ** 2
    b["near"] = h.places[int(np.argmin(d))][0]
    if not b["city"]:
        b["city"] = b["near"]

print(f"bars in extract: {len(h.bars)}, inside WI: {len(bars)}, after dedupe: {len(dedup)}")
print(f"with a name: {sum(1 for b in dedup if b['name'])}, with a street address: {sum(1 for b in dedup if b['address'])}")
print(f"major road segments: {len(h.roads)}")

with open(f"{OUT}/bars.json", "w") as f:
    json.dump(dedup, f)
with open(f"{OUT}/bars.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "type", "address", "city", "lat", "lon", "osm"])
    w.writeheader()
    for b in sorted(dedup, key=lambda b: (b["city"].lower(), b["name"].lower())):
        w.writerow({k: b[k] for k in w.fieldnames})
with open(f"{OUT}/roads.json", "w") as f:
    json.dump(h.roads, f, separators=(",", ":"))
