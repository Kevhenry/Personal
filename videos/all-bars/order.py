"""Choose the order to visit every bar: a shortest tour (LKH solver), opened at its longest hop.

usage: python3 order.py bars.json ordered.json
Distances here are straight-line; the road route between consecutive bars comes from route.py.
"""
import json, math, sys, time
import elkai

src, dst = sys.argv[1:3]
bars = json.load(open(src))
lat0 = sum(b["lat"] for b in bars) / len(bars)
kx, ky = 111.32 * math.cos(math.radians(lat0)), 110.57  # km per degree
pts = {str(i): (b["lon"] * kx, b["lat"] * ky) for i, b in enumerate(bars)}

t = time.time()
tour = [int(i) for i in elkai.Coordinates2D(pts).solve_tsp(runs=4)]
if tour[0] == tour[-1]:
    tour = tour[:-1]
print(f"solved {len(tour)} stops in {time.time() - t:.0f}s")

def d(i, j):
    return math.dist(pts[str(i)], pts[str(j)])

n = len(tour)
cut = max(range(n), key=lambda k: d(tour[k], tour[(k + 1) % n]))
path = tour[cut + 1:] + tour[:cut + 1]
# start in the south-east (Milwaukee side) so the trip reads naturally
if bars[path[0]]["lon"] * kx - bars[path[0]]["lat"] * ky < bars[path[-1]]["lon"] * kx - bars[path[-1]]["lat"] * ky:
    path.reverse()
print(f"straight-line length: {sum(d(path[k], path[k + 1]) for k in range(n - 1)) / 1.609:.0f} mi; "
      f"start {bars[path[0]]['name']} ({bars[path[0]]['city']}), end {bars[path[-1]]['name']} ({bars[path[-1]]['city']})")
json.dump([bars[i] for i in path], open(dst, "w"))
