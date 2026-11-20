"""Fetch the fastest driving route through the ordered bars from the public OSRM server.

usage: python3 route.py ordered.json route.json cache_dir
Requests go in batches of 100 stops, one per ~1.2 s (OSRM demo-server usage policy), cached on disk.
"""
import json, os, sys, time, urllib.request

src, dst, cache = sys.argv[1:4]
os.makedirs(cache, exist_ok=True)
bars = json.load(open(src))
B = 100
chunks = [list(range(s, min(s + B, len(bars)))) for s in range(0, len(bars) - 1, B - 1)]

coords, cumd, cumt, stop_idx = [], [], [], [0]
D = T = 0.0
for ci, ch in enumerate(chunks):
    fn = f"{cache}/chunk{ci:04d}.json"
    if not os.path.exists(fn):
        loc = ";".join(f"{bars[i]['lon']:.6f},{bars[i]['lat']:.6f}" for i in ch)
        url = (f"https://router.project-osrm.org/route/v1/driving/{loc}"
               "?overview=full&geometries=geojson&annotations=distance,duration")
        for attempt in range(5):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "route-video-script/1.0"})
                data = json.load(urllib.request.urlopen(req, timeout=120))
                if data.get("code") == "Ok":
                    break
                print("osrm said", data.get("code"), data.get("message"))
            except Exception as e:  # network hiccup / rate limit
                print(f"chunk {ci} attempt {attempt}: {e}")
            time.sleep(5 * (attempt + 1))
        else:
            sys.exit(f"chunk {ci} failed")
        json.dump(data, open(fn, "w"))
        time.sleep(1.2)
    data = json.load(open(fn))
    r = data["routes"][0]
    geom = r["geometry"]["coordinates"]
    nseg = [len(l["annotation"]["distance"]) for l in r["legs"]]
    assert len(geom) == sum(nseg) + 1, (ci, len(geom), sum(nseg))
    gi = 0
    if not coords:
        coords.append(geom[0]); cumd.append(0.0); cumt.append(0.0)
    for leg, n in zip(r["legs"], nseg):
        for k in range(n):
            D += leg["annotation"]["distance"][k]
            T += leg["annotation"]["duration"][k]
            coords.append(geom[gi + k + 1]); cumd.append(D); cumt.append(T)
        gi += n
        stop_idx.append(len(coords) - 1)
    print(f"chunk {ci + 1}/{len(chunks)}  {D / 1609.34:,.0f} mi so far", flush=True)

assert len(stop_idx) == len(bars), (len(stop_idx), len(bars))
json.dump({"coords": [[round(x, 5), round(y, 5)] for x, y in coords],
           "cumd": [round(v) for v in cumd], "cumt": [round(v) for v in cumt],
           "stops": stop_idx, "total_m": D, "total_s": T}, open(dst, "w"), separators=(",", ":"))
print(f"total {D / 1609.34:,.0f} miles, {T / 3600:,.0f} hours of driving, {len(coords):,} points")
