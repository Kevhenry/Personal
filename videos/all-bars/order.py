"""Choose the order to visit every bar: a shortest tour (LKH solver), opened in downtown Milwaukee.

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
# elkai rounds distances to integers: solve in metres, or dense city blocks collapse to 0 and LKH crawls
tour = [int(i) for i in elkai.Coordinates2D({k: (x * 1000, y * 1000) for k, (x, y) in pts.items()}).solve_tsp(runs=4)]
if tour[0] == tour[-1]:
    tour = tour[:-1]
print(f"solved {len(tour)} stops in {time.time() - t:.0f}s")

def d(i, j):
    return math.dist(pts[str(i)], pts[str(j)])

n = len(tour)
# start at the bar nearest downtown Milwaukee; open the loop on the longer of that stop's two hops,
# so the trip runs Milwaukee -> around the state -> back into Milwaukee
hub = (-87.9097 * kx, 43.0418 * ky)
k = min(range(n), key=lambda i: math.dist(pts[str(tour[i])], hub))
if d(tour[k - 1], tour[k]) >= d(tour[k], tour[(k + 1) % n]):
    path = tour[k:] + tour[:k]            # drop hop (k-1 -> k)
else:
    path = (tour[k:] + tour[:k])[::-1]    # drop hop (k -> k+1)
    path = path[-1:] + path[:-1]
print(f"straight-line length: {sum(d(path[k], path[k + 1]) for k in range(n - 1)) / 1.609:.0f} mi; "
      f"start {bars[path[0]]['name']} ({bars[path[0]]['city']}), end {bars[path[-1]]['name']} ({bars[path[-1]]['city']})")
json.dump([bars[i] for i in path], open(dst, "w"))
