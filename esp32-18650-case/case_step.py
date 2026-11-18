"""
CadQuery version of case.scad, used to export STEP files (true solids with
real cylinders, fillets and planes) for Onshape, Fusion 360, FreeCAD, etc.

The dimensions match case.scad. If you change a value there, change it here
too and re-run:

    pip install cadquery
    python3 case_step.py

Writes:
    step/case_assembled.step  tray + lid as two bodies, in assembled position
    step/tray.step            tray only
    step/lid.step             lid only (assembled orientation, not flipped)
"""
import os
import cadquery as cq
from cadquery import Vector

# ---------------- parameters (same as case.scad) ----------------
board_l, board_w, pcb_t = 99.0, 29.5, 1.6
bottom_clear, top_clear, fit = 5.5, 22.0, 0.4
hole_inset_x, hole_inset_y = 2.2, 2.2
screw = "M2.5"
holder_x0, holder_len, holder_w = 18, 78, 21
usba_overhang, usba_w, usba_h = 3.0, 14.0, 7.2
usbc_x, usbc_w, usbc_h, usbc_dz = 78.6, 9.6, 3.8, 1.6
micro_x, micro_w, micro_h, micro_dz = 91.8, 8.6, 3.6, 1.4
plug_pocket = True
btn_x, btn_w, btn_h = 12.0, 6.0, 4.4
sw_x, sw_w, sw_h = 9.5, 9.0, 4.2
led_windows, led_x, led_y, led_d = True, [21.1, 25.4, 29.4, 33.4, 37.4], 5.4, 2.0
wall, floor_t, roof_t, corner_r, edge_ch = 2.0, 1.6, 1.8, 3.0, 0.8
end_bay = 7.0
wire_exit, wire_d = True, 4.0
vents, vent_x0, vent_x1 = True, 45, 72

# ---------------- derived ----------------
gap_a = max(fit, usba_overhang - wall)
bx0, by0 = wall + gap_a, wall + fit
in_l, in_w = gap_a + board_l + end_bay, board_w + 2 * fit
Lo, Wo = in_l + 2 * wall, in_w + 2 * wall
zb = floor_t + bottom_clear
zt = zb + pcb_t
zs = zt
zc = zt + top_clear
Ho = zc + roof_t

m3 = screw == "M3"
s_clear, s_pilot = (3.4, 2.6) if m3 else (2.9, 2.15)
s_head, s_cb = (6.2, 3.0) if m3 else (5.2, 2.6)
post_d, boss_d = 5.0, 6.5
pilot_len = min(13, top_clear - 1.2)

cx = lambda x: bx0 + x
cy = lambda y: by0 + y

hole_pts = [(cx(hole_inset_x), cy(hole_inset_y)),
            (cx(hole_inset_x), cy(board_w - hole_inset_y))]
bay_x = bx0 + board_l + end_bay / 2 + 0.3
bay_pts = [(bay_x, Wo / 2 - 8.5), (bay_x, Wo / 2 + 8.5)]
pad_pts = [(cx(board_l - hole_inset_x), cy(hole_inset_y)),
           (cx(board_l - hole_inset_x), cy(board_w - hole_inset_y))]


# ---------------- helpers ----------------
def box(x, y, z, lx, ly, lz):
    return cq.Workplane().add(cq.Solid.makeBox(lx, ly, lz, Vector(x, y, z)))


def cyl(d, h, x, y, z, direction=(0, 0, 1)):
    return cq.Workplane().add(
        cq.Solid.makeCylinder(d / 2, h, Vector(x, y, z), Vector(*direction)))


def cone(d1, d2, h, x, y, z):
    return cq.Workplane().add(cq.Solid.makeCone(d1 / 2, d2 / 2, h, Vector(x, y, z)))


def side_cut(side, xc, w, z0, z1, depth=wall + fit + 0.3, r=0.8):
    h = z1 - z0
    y0 = -1.0 if side == "front" else Wo - depth
    d = depth + 1.0  # run 1 mm past the outer surface
    if side == "back":
        y0 = Wo - depth
    b = box(xc - w / 2, y0, z0, w, d, h)
    rr = min(r, w / 2 - 0.01, h / 2 - 0.01)
    if rr >= 0.05:
        b = b.edges("|Y").fillet(rr)
    return b


# ---------------- body ----------------
outer = (cq.Workplane().box(Lo, Wo, Ho, centered=False)
         .edges("|Z").fillet(corner_r)
         .faces(">Z").edges().chamfer(edge_ch)
         .faces("<Z").edges().chamfer(edge_ch))
cavity = (box(wall, wall, floor_t, in_l, in_w, zc - floor_t + 5)
          .edges("|Z").fillet(1.0))
cavity = cavity.intersect(box(0, 0, floor_t, Lo, Wo, zc - floor_t))
body = outer.cut(cavity)

for x, y in hole_pts:
    body = body.union(cone(s_head + 2.2, post_d, bottom_clear, x, y, floor_t))
    body = body.union(cyl(post_d, top_clear, x, y, zt))
for x, y in pad_pts:
    body = body.union(cone(5, 3.4, bottom_clear, x, y, floor_t))
for x, y in bay_pts:
    body = body.union(cyl(boss_d, zc - floor_t, x, y, floor_t))
    body = body.union(box(x, y - boss_d / 2, floor_t, Lo - wall - x + 0.01, boss_d, zc - floor_t))

keepout = box(cx(holder_x0) - 0.6, cy(board_w / 2 - holder_w / 2) - 0.6, zt,
              holder_len + 1.2, holder_w + 1.2, top_clear + 1)
for y in (cy(-fit), cy(board_w - 3.2)):
    blk = box(cx(board_l - 7), y, zt, 7 + fit, 3.2 + fit, top_clear).cut(keepout)
    body = body.union(blk)

# ---------------- cutouts ----------------
cuts = []
for x, y in hole_pts + bay_pts:
    cuts += [cyl(s_clear, zs + 1, x, y, -1),
             cyl(s_head, s_cb + 1, x, y, -1),
             cyl(s_pilot, pilot_len, x, y, zs)]

cuts.append(box(-1, cy(board_w / 2) - usba_w / 2, zs, wall + gap_a + 1, usba_w, usba_h))

uc = zb - usbc_dz
cuts.append(side_cut("front", cx(usbc_x), usbc_w, uc - usbc_h / 2, zs + 0.01))
um = zb - micro_dz
cuts.append(side_cut("back", cx(micro_x), micro_w, um - micro_h / 2, zs + 0.01))
if plug_pocket:
    cuts.append(side_cut("front", cx(usbc_x), usbc_w + 3.4, uc - usbc_h / 2 - 1.7,
                         uc + usbc_h / 2 + 1.7, depth=wall - 0.8, r=1.5))
    cuts.append(side_cut("back", cx(micro_x), micro_w + 3.4, um - micro_h / 2 - 1.7,
                         um + micro_h / 2 + 1.7, depth=wall - 0.8, r=1.5))

cuts.append(side_cut("front", cx(btn_x), btn_w, zs - 0.01, zt + btn_h, r=0))
cuts.append(side_cut("back", cx(sw_x), sw_w, zs - 0.01, zt + sw_h, r=0))

if led_windows:
    for x in led_x:
        cuts.append(cyl(led_d, floor_t + 2, cx(x), cy(led_y), -1))

if vents:
    slot_len = (board_w - 16) + 1.8
    x = vent_x0
    while x <= vent_x1 + 1e-6:
        cuts.append(cq.Workplane("XY").workplane(offset=-1)
                    .center(cx(x), cy(board_w / 2))
                    .slot2D(slot_len, 1.8, angle=90).extrude(floor_t + 2))
        x += 4

if wire_exit:
    cuts.append(cyl(wire_d, wall + 2, Lo - wall - 1, Wo / 2, zs, direction=(1, 0, 0)))

full = body
for c in cuts:
    full = full.cut(c)

big = 50
tray = full.intersect(box(-big, -big, -big, Lo + 2 * big, Wo + 2 * big, zs + big))
lid = full.intersect(box(-big, -big, zs, Lo + 2 * big, Wo + 2 * big, Ho + big))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "step")
os.makedirs(out, exist_ok=True)
cq.exporters.export(tray, os.path.join(out, "tray.step"))
cq.exporters.export(lid, os.path.join(out, "lid.step"))

assy = cq.Assembly(name="battery_case")
assy.add(tray, name="tray", color=cq.Color(1.0, 0.55, 0.1))
assy.add(lid, name="lid", color=cq.Color(0.95, 0.85, 0.6))
assy.export(os.path.join(out, "case_assembled.step"))

for name, part in (("tray", tray), ("lid", lid)):
    s = part.val()
    print(f"{name}: valid={s.isValid()} solids={len(part.solids().vals())} "
          f"volume={s.Volume():.1f} mm^3")
print(f"outer size {Lo:.1f} x {Wo:.1f} x {Ho:.1f} mm")
