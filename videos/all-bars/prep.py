"""Pack the ordered bars, road route and basemap into one compact file for the renderer.

usage: python3 prep.py ordered.json route.json roads.json|- states.json out.json
Coordinates are converted to Web-Mercator radians; the route gets several levels of detail.
"""
import json, math, sys
import numpy as np
from simplification.cutil import simplify_coords_idx

bars_f, route_f, roads_f, states_f, out_f = sys.argv[1:6]
bars = json.load(open(bars_f))
route = json.load(open(route_f))
roads = json.load(open(roads_f)) if roads_f != "-" else []

def merc(lon, lat):
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    return np.radians(lon), np.log(np.tan(np.pi / 4 + np.radians(lat) / 2))

c = np.array(route["coords"])
x, y = merc(c[:, 0], c[:, 1])
xy = np.column_stack([x, y])
stops = np.array(route["stops"])

# level 0: drop points that add nothing (< ~3 m), but always keep the stops
keep = set(simplify_coords_idx(xy.tolist(), 5e-7)) | set(stops.tolist())
base = np.array(sorted(keep))
remap = {int(old): new for new, old in enumerate(base)}
bx, by = x[base], y[base]
cumd = np.array(route["cumd"])[base]
cumt = np.array(route["cumt"])[base]
lods = []
for tol in (4e-6, 2e-5, 8e-5):
    lods.append(simplify_coords_idx(np.column_stack([bx, by]).tolist(), tol))
print(f"route points: {len(x):,} -> {len(base):,}; lods {[len(l) for l in lods]}")

bx_, by_ = merc([b["lon"] for b in bars], [b["lat"] for b in bars])
out = {
    "route": {"x": np.round(bx, 7).tolist(), "y": np.round(by, 7).tolist(),
              "d": cumd.astype(int).tolist(), "t": cumt.astype(int).tolist(), "lods": lods},
    "bars": {"x": np.round(bx_, 7).tolist(), "y": np.round(by_, 7).tolist(),
             "name": [b["name"] or "Unnamed bar" for b in bars],
             "city": [b.get("city", "") for b in bars],
             "stop": [remap[int(s)] for s in stops]},
    "roads": [],
    "states": json.load(open(states_f)),
    "total_m": route["total_m"], "total_s": route["total_s"],
}
for cls, pts in roads:
    p = np.array(pts)
    rx, ry = merc(p[:, 0], p[:, 1])
    out["roads"].append([cls, np.round(np.column_stack([rx, ry]).ravel(), 6).tolist()])
json.dump(out, open(out_f, "w"), separators=(",", ":"))
print(f"wrote {out_f}: {len(bars)} bars, {len(out['roads'])} road lines")
