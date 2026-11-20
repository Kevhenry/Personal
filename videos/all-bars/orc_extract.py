"""Fallback for when the Geofabrik .pbf can't be downloaded: cut the data extract.py needs
straight out of the OpenStreetMap planet ORC file on AWS Open Data (s3://osm-pds), reading
only the columns we need, and write it as a small .osm XML file that extract.py reads as-is.

usage: python3 orc_extract.py out.osm [threads]

Keeps, inside a box padded around Wisconsin:
  nodes tagged amenity=bar|pub|biergarten or place=city|town|village (with all their tags)
  ways  tagged amenity=bar|pub|biergarten (all tags) or highway=motorway|trunk|primary|secondary
  the untagged nodes those ways use
Relations are skipped (extract.py skips them too).
"""
import os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor
from xml.sax.saxutils import quoteattr
import numpy as np
import pyarrow as pa, pyarrow.compute as pc, pyarrow.fs as pafs, pyarrow.orc as orc

OUT = sys.argv[1]
THREADS = int(sys.argv[2]) if len(sys.argv) > 2 else 32
KEY = "osm-pds/planet/planet-latest.orc"
LON0, LON1, LAT0, LAT1 = -93.6, -86.2, 41.9, 47.6
BAR = ["bar", "pub", "biergarten"]
PLACE = ["city", "town", "village"]
ROAD = ["motorway", "trunk", "primary", "secondary"]

proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
s3kw = dict(anonymous=True, region="us-east-1")
if proxy:
    s3kw["proxy_options"] = proxy
if os.path.exists("/root/.ccr/ca-bundle.crt"):
    s3kw["tls_ca_file_path"] = "/root/.ccr/ca-bundle.crt"
s3 = pafs.S3FileSystem(**s3kw)
local = threading.local()


def orcfile():
    if not hasattr(local, "f"):
        local.f = orc.ORCFile(s3.open_input_file(KEY))
    return local.f


def read(i, cols):
    for attempt in range(6):
        try:
            return orcfile().read_stripe(i, columns=cols)
        except Exception as e:
            print(f"stripe {i} attempt {attempt}: {e}", flush=True)
            local.__dict__.pop("f", None)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"stripe {i} failed")


def tag_rows(tags, rules):
    """Row indices whose tags contain any (key, allowed values) rule."""
    if len(tags.keys) == 0:
        return np.zeros(0, np.int64)
    m = None
    for k, vals in rules:
        x = pc.and_(pc.equal(tags.keys, k), pc.is_in(tags.items, pa.array(vals)))
        m = x if m is None else pc.or_(m, x)
    m = np.asarray(m.fill_null(False))
    offs = np.asarray(tags.offsets)
    parent = np.repeat(np.arange(len(tags)), np.diff(offs))
    assert len(parent) == len(m), (len(parent), len(m))
    return np.unique(parent[m])


def node_stripe(i):
    b = read(i, ["id", "type", "tags", "lat", "lon"])
    typ = np.asarray(b.column("type").to_numpy(zero_copy_only=False)) == "node"
    lat = pc.cast(b.column("lat"), pa.float64()).fill_null(-999).to_numpy()
    lon = pc.cast(b.column("lon"), pa.float64()).fill_null(-999).to_numpy()
    inb = typ & (lat >= LAT0) & (lat <= LAT1) & (lon >= LON0) & (lon <= LON1)
    ids = b.column("id").to_numpy()
    tagged = {}
    rows = tag_rows(b.column("tags"), [("amenity", BAR), ("place", PLACE)])
    rows = rows[inb[rows]]
    if len(rows):
        t = b.column("tags").take(pa.array(rows)).to_pylist()
        for r, tl in zip(rows, t):
            tagged[int(ids[r])] = (float(lat[r]), float(lon[r]), dict(tl))
    return ids[inb], lat[inb], lon[inb], tagged


def way_stripe(i, bbox_ids):
    b = read(i, ["id", "type", "tags", "nds"])
    typ = np.asarray(b.column("type").to_numpy(zero_copy_only=False)) == "way"
    rows = tag_rows(b.column("tags"), [("amenity", BAR), ("highway", ROAD)])
    rows = rows[typ[rows]]
    out = []
    if not len(rows):
        return out
    ids = b.column("id").to_numpy()
    tl = b.column("tags").take(pa.array(rows)).to_pylist()
    nl = b.column("nds").take(pa.array(rows))
    for r, tags, nds in zip(rows, tl, nl.to_pylist()):
        refs = np.array([n["ref"] for n in nds], np.int64)
        if not len(refs):
            continue
        pos = np.searchsorted(bbox_ids, refs).clip(0, len(bbox_ids) - 1)
        ok = bbox_ids[pos] == refs
        if not ok.any():
            continue
        tags = dict(tags)
        if tags.get("amenity") not in BAR:
            tags = {"highway": tags["highway"]}
        out.append((int(ids[r]), tags, refs[ok]))
    return out


def stripe_type(f, i, last):
    c = f.read_stripe(i, columns=["type"]).column(0)
    return c[len(c) - 1 if last else 0].as_py()


def main():
    f = orcfile()
    n = f.nstripes
    lo, hi = 0, n - 1  # first stripe containing a way
    while lo < hi:
        m = (lo + hi) // 2
        lo, hi = (m + 1, hi) if stripe_type(f, m, True) == "node" else (lo, m)
    wfirst = lo
    lo, hi = wfirst, n - 1  # first stripe containing a relation
    while lo < hi:
        m = (lo + hi) // 2
        lo, hi = (m + 1, hi) if stripe_type(f, m, True) != "relation" else (lo, m)
    wlast = lo
    print(f"{n} stripes; nodes 0-{wfirst}, ways {wfirst}-{wlast}", flush=True)

    t0 = time.time()
    I, LA, LO, TAG = [], [], [], {}
    with ThreadPoolExecutor(THREADS) as ex:
        for k, (ids, la, lo_, tg) in enumerate(ex.map(node_stripe, range(wfirst + 1))):
            I.append(ids); LA.append(la); LO.append(lo_); TAG.update(tg)
            if k % 100 == 0:
                print(f"nodes: stripe {k}/{wfirst}  {sum(map(len, I)):,} in box  {time.time() - t0:.0f}s", flush=True)
    I, LA, LO = np.concatenate(I), np.concatenate(LA), np.concatenate(LO)
    o = np.argsort(I, kind="stable")
    I, LA, LO = I[o], LA[o], LO[o]
    print(f"nodes in box: {len(I):,}, tagged keepers: {len(TAG):,}  ({time.time() - t0:.0f}s)", flush=True)

    ways = []
    with ThreadPoolExecutor(THREADS) as ex:
        for k, w in enumerate(ex.map(lambda i: way_stripe(i, I), range(wfirst, wlast + 1))):
            ways.extend(w)
            if k % 100 == 0:
                print(f"ways: stripe {k}/{wlast - wfirst}  {len(ways):,} kept  {time.time() - t0:.0f}s", flush=True)
    ways.sort(key=lambda w: w[0])
    print(f"ways kept: {len(ways):,}  ({time.time() - t0:.0f}s)", flush=True)

    need = np.unique(np.concatenate([w[2] for w in ways] + [np.array(list(TAG), np.int64)]))
    pos = np.searchsorted(I, need)
    with open(OUT, "w", encoding="utf-8") as g:
        g.write('<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="orc_extract.py">\n')
        for nid, p in zip(need.tolist(), pos.tolist()):
            if nid in TAG:
                la, lo_, tags = TAG[nid]
                g.write(f'<node id="{nid}" version="1" lat="{la:.7f}" lon="{lo_:.7f}">')
                g.write("".join(f"<tag k={quoteattr(k)} v={quoteattr(v or '')}/>" for k, v in tags.items()))
                g.write("</node>\n")
            else:
                g.write(f'<node id="{nid}" version="1" lat="{LA[p]:.7f}" lon="{LO[p]:.7f}"/>\n')
        for wid, tags, refs in ways:
            g.write(f'<way id="{wid}" version="1">')
            g.write("".join(f'<nd ref="{r}"/>' for r in refs.tolist()))
            g.write("".join(f"<tag k={quoteattr(k)} v={quoteattr(v or '')}/>" for k, v in tags.items()))
            g.write("</way>\n")
        g.write("</osm>\n")
    print(f"wrote {OUT}: {len(need):,} nodes, {len(ways):,} ways  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
