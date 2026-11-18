// =====================================================================
//  18650 Battery Shield (USB-A out / USB-C + micro-USB in) - PETG case
//  Two parts: TRAY (bottom, holds the PCB) + LID (covers the battery).
//  Held together by 4 self-tapping screws from underneath.
//
//  Coordinate convention for every "_x" / "_y" value below:
//    x = distance along the PCB, measured from the USB-A end
//    y = distance across the PCB, measured from the edge that has the
//        push button (K1) and the USB-C port ("front" edge)
//    The slide switch (SW1) and micro-USB are on the opposite ("back") edge.
//
//  Defaults were estimated from photos. MEASURE YOUR BOARD WITH CALIPERS
//  and adjust the values marked  <-- MEASURE  before printing.
// =====================================================================

/* [What to render] */
part = "plate"; // [plate, tray, lid, assembly]

/* [Board - measure these] */
board_l      = 99.0;   // <-- MEASURE PCB length (no connectors)
board_w      = 29.5;   // <-- MEASURE PCB width
pcb_t        = 1.6;
bottom_clear = 5.5;    // <-- MEASURE tallest part on the underside (+0.5)
top_clear    = 22.0;   // <-- MEASURE PCB top to top of the 18650 (+1)
fit          = 0.4;    // gap between PCB edge and case wall

/* [Mounting holes in the PCB corners] */
hole_inset_x = 2.2;    // <-- MEASURE hole centre from PCB end
hole_inset_y = 2.2;    // <-- MEASURE hole centre from PCB side
screw        = "M2.5"; // [M2.5, M3]

/* [Battery holder envelope (keep-out zone for the lid)] */
holder_x0    = 18;     // where the holder starts (from USB-A end)
holder_len   = 78;
holder_w     = 21;

/* [USB-A output (top side, PCB end)] */
usba_overhang = 3.0;   // <-- MEASURE how far the USB-A shell sticks past the PCB end
usba_w        = 14.0;
usba_h        = 7.2;   // above PCB top

/* [USB-C input (UNDERSIDE, front edge)] */
usbc_x   = 78.6;       // <-- MEASURE centre of the connector
usbc_w   = 9.6;
usbc_h   = 3.8;
usbc_dz  = 1.6;        // connector centre below PCB bottom

/* [Micro-USB input (UNDERSIDE, back edge)] */
micro_x  = 91.8;       // <-- MEASURE
micro_w  = 8.6;
micro_h  = 3.6;
micro_dz = 1.4;

plug_pocket = true;    // recess the outside so cable plugs seat fully

/* [Push button K1 (top side, front edge)] */
btn_x = 12.0;          // <-- MEASURE
btn_w = 6.0;
btn_h = 4.4;           // window height above PCB top

/* [Slide switch SW1 (top side, back edge)] */
sw_x = 9.5;            // <-- MEASURE
sw_w = 9.0;
sw_h = 4.2;

/* [Charge / level LEDs (UNDERSIDE)] */
led_windows = true;
led_x = [21.1, 25.4, 29.4, 33.4, 37.4]; // <-- MEASURE
led_y = 5.4;
led_d = 2.0;

/* [Case] */
wall      = 2.0;
floor_t   = 1.6;
roof_t    = 1.8;
corner_r  = 3.0;
edge_ch   = 0.8;
end_bay   = 7.0;       // space past the battery end for 2 screws + cable exit
wire_exit = true;      // cable hole in the battery-end wall (for ESP32 power leads)
wire_d    = 4.0;
vents     = true;      // floor vents under the boost converter
vent_x0   = 45;
vent_x1   = 72;
mount_ears = false;    // screw tabs on both ends of the tray
ear_hole   = 3.5;

$fn = 48;

// ---------------------------------------------------------------------
// Derived dimensions
// ---------------------------------------------------------------------
eps   = 0.01;
gap_a = max(fit, usba_overhang - wall);   // USB-A face ends flush with the wall
bx0   = wall + gap_a;                     // PCB origin in case coords
by0   = wall + fit;
in_l  = gap_a + board_l + end_bay;
in_w  = board_w + 2*fit;
Lo    = in_l + 2*wall;
Wo    = in_w + 2*wall;
zb    = floor_t + bottom_clear;           // PCB bottom
zt    = zb + pcb_t;                       // PCB top  == split plane
zs    = zt;
zc    = zt + top_clear;                   // cavity ceiling
Ho    = zc + roof_t;

s_clear = screw == "M3" ? 3.4 : 2.9;
s_pilot = screw == "M3" ? 2.6 : 2.15;
s_head  = screw == "M3" ? 6.2 : 5.2;
s_cb    = screw == "M3" ? 3.0 : 2.6;      // counterbore depth (screw head)

post_d  = 5.0;                             // lid post / standoff top
boss_d  = 6.5;                             // battery-end bosses

function cx(x) = bx0 + x;
function cy(y) = by0 + y;

// screw positions
hole_pts = [ [cx(hole_inset_x), cy(hole_inset_y)],
             [cx(hole_inset_x), cy(board_w - hole_inset_y)] ];
bay_x    = bx0 + board_l + end_bay/2 + 0.3;
bay_pts  = [ [bay_x, Wo/2 - 8.5], [bay_x, Wo/2 + 8.5] ];
pad_pts  = [ [cx(board_l - hole_inset_x), cy(hole_inset_y)],
             [cx(board_l - hole_inset_x), cy(board_w - hole_inset_y)] ];

// ---------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------
module rbox(l, w, h, r, ch=0) {
    hull() for (x=[r, l-r], y=[r, w-r]) translate([x, y, 0]) {
        if (ch > 0) {
            cylinder(r1=r-ch, r2=r, h=ch);
            translate([0,0,h-ch]) cylinder(r1=r, r2=r-ch, h=ch);
        }
        translate([0,0,ch]) cylinder(r=r, h=h-2*ch);
    }
}

// rectangular window through a side wall (y = 0 or y = Wo side)
// x centre, width, z range, depth measured from the outer surface
module side_cut(side, xc, w, z0, z1, depth=wall+fit+0.3, r=0.8) {
    yo = side == "front" ? -eps : Wo + eps;
    dir = side == "front" ? 1 : -1;
    h = z1 - z0;
    rr = min(r, w/2 - eps, h/2 - eps);
    translate([xc - w/2, side == "front" ? yo : yo - depth, z0])
        if (rr < 0.05) cube([w, depth, h]);
        else hull() for (x=[rr, w-rr], z=[rr, h-rr])
            translate([x, 0, z]) rotate([-90,0,0]) cylinder(r=rr, h=depth);
}

// battery holder keep-out (lid features must not intrude)
module holder_keepout(c=0.6) {
    translate([cx(holder_x0) - c, cy(board_w/2 - holder_w/2) - c, zt - eps])
        cube([holder_len + 2*c, holder_w + 2*c, top_clear + 1]);
}

// ---------------------------------------------------------------------
// Solid model of the closed case (split later)
// ---------------------------------------------------------------------
module body_solid() {
    difference() {
        rbox(Lo, Wo, Ho, corner_r, edge_ch);
        translate([wall, wall, floor_t])
            rbox(in_l, in_w, zc - floor_t, 1.0);
    }

    // standoffs under the PCB at the USB-A end (screws go through PCB)
    for (p = hole_pts) translate([p[0], p[1], floor_t - eps])
        cylinder(d1=s_head + 2.2, d2=post_d, h=bottom_clear + eps);

    // support pads under the PCB at the battery end (no screw)
    for (p = pad_pts) translate([p[0], p[1], floor_t - eps])
        cylinder(d1=5, d2=3.4, h=bottom_clear + eps);

    // lid posts above the PCB at the USB-A end
    for (p = hole_pts) translate([p[0], p[1], zt + 0.02])
        cylinder(d=post_d, h=top_clear + eps);

    // full-height bosses in the end bay
    for (p = bay_pts) translate([p[0], p[1], floor_t - eps])
        cylinder(d=boss_d, h=zc - floor_t + 2*eps);
    // tie the bosses into the end wall
    for (p = bay_pts) translate([p[0], p[1] - boss_d/2, floor_t - eps])
        cube([Lo - wall - p[0] + eps, boss_d, zc - floor_t + 2*eps]);

    // lid clamp blocks: press the battery end of the PCB down
    difference() {
        for (y = [cy(-fit) - eps, cy(board_w - 3.2)])
            translate([cx(board_l - 7), y, zt + 0.02])
                cube([7 + fit, 3.2 + fit + eps, top_clear + eps]);
        holder_keepout();
    }

    if (mount_ears) {
        translate([0, Wo/2, 0]) ear();
        translate([Lo, Wo/2, 0]) mirror([1,0,0]) ear();
    }
}

module ear() {
    difference() {
        hull() {
            translate([-eps, -7, 0]) cube([corner_r, 14, 3]);
            translate([-6, 0, 0]) cylinder(d=10, h=3);
        }
        translate([-6, 0, -1]) cylinder(d=ear_hole, h=5);
    }
}

module cutouts() {
    // --- screws through the PCB (USB-A end) ---
    for (p = hole_pts) translate([p[0], p[1], 0]) {
        translate([0,0,-1]) cylinder(d=s_clear, h=zs + 1 + eps);
        translate([0,0,-1]) cylinder(d=s_head, h=s_cb + 1);
        translate([0,0,zs - eps]) cylinder(d=s_pilot, h=min(13, top_clear - 1.2));
    }
    // --- screws in the end bay ---
    for (p = bay_pts) translate([p[0], p[1], 0]) {
        translate([0,0,-1]) cylinder(d=s_clear, h=zs + 1 + eps);
        translate([0,0,-1]) cylinder(d=s_head, h=s_cb + 1);
        translate([0,0,zs - eps]) cylinder(d=s_pilot, h=min(13, top_clear - 1.2));
    }

    // --- USB-A notch in the end wall (lid) ---
    translate([-eps - 1, cy(board_w/2) - usba_w/2, zs - eps])
        cube([wall + gap_a + 1, usba_w, usba_h + eps]);

    // --- USB-C (front, underside) ---
    uc = zb - usbc_dz;
    side_cut("front", cx(usbc_x), usbc_w, uc - usbc_h/2, zs + eps);
    if (plug_pocket)
        side_cut("front", cx(usbc_x), usbc_w + 3.4, uc - usbc_h/2 - 1.7,
                 uc + usbc_h/2 + 1.7, depth=wall - 0.8 + eps, r=1.5);

    // --- micro-USB (back, underside) ---
    um = zb - micro_dz;
    side_cut("back", cx(micro_x), micro_w, um - micro_h/2, zs + eps);
    if (plug_pocket)
        side_cut("back", cx(micro_x), micro_w + 3.4, um - micro_h/2 - 1.7,
                 um + micro_h/2 + 1.7, depth=wall - 0.8 + eps, r=1.5);

    // --- push button window (front, lid, open at the seam) ---
    side_cut("front", cx(btn_x), btn_w, zs - eps, zt + btn_h, r=0);

    // --- slide switch window (back, lid, open at the seam) ---
    side_cut("back", cx(sw_x), sw_w, zs - eps, zt + sw_h, r=0);

    // --- LED windows in the floor ---
    if (led_windows) for (x = led_x)
        translate([cx(x), cy(led_y), -1]) cylinder(d=led_d, h=floor_t + 2);

    // --- floor vents under the boost converter ---
    if (vents) for (x = [vent_x0 : 4 : vent_x1])
        hull() for (y = [cy(8), cy(board_w - 8)])
            translate([cx(x), y, -1]) cylinder(d=1.8, h=floor_t + 2, $fn=16);

    // --- cable exit in the battery-end wall (split by the seam) ---
    if (wire_exit)
        translate([Lo - wall - 1, Wo/2, zs]) rotate([0,90,0])
            cylinder(d=wire_d, h=wall + 2);
}

module full_case() { difference() { body_solid(); cutouts(); } }

module tray() {
    intersection() {
        full_case();
        translate([-20, -20, -1]) cube([Lo + 40, Wo + 40, zs + 1]);
    }
}

module lid() {
    intersection() {
        full_case();
        translate([-20, -20, zs]) cube([Lo + 40, Wo + 40, Ho]);
    }
}

// lid flipped onto its roof for printing
module lid_print() { translate([0, Wo, Ho]) rotate([180, 0, 0]) lid(); }

// rough stand-ins for the PCB / holder / cell, for checking fit
module dummy_board() {
    color("darkgreen") translate([cx(0), cy(0), zb]) cube([board_l, board_w, pcb_t]);
    color("dimgray") translate([cx(holder_x0), cy(board_w/2 - holder_w/2), zt])
        cube([holder_len, holder_w, 3]);
    color("royalblue") translate([cx(holder_x0 + 5), cy(board_w/2), zt + 1 + 9.3])
        rotate([0,90,0]) cylinder(d=18.6, h=65.2);
    color("silver") translate([cx(-usba_overhang), cy(board_w/2) - 6.6, zt])
        cube([14, 13.2, 6.8]);
    color("silver") translate([cx(usbc_x) - 4.5, cy(-0.3), zb - 3.2]) cube([9, 7.4, 3.2]);
    color("silver") translate([cx(micro_x) - 3.9, cy(board_w - 5), zb - 2.8]) cube([7.8, 5.3, 2.8]);
}

if (part == "tray") tray();
else if (part == "lid") lid_print();
else if (part == "assembly") {
    color("orange") tray();
    dummy_board();
    color("orange", 0.35) lid();
}
else { // plate: both parts side by side, print orientation
    tray();
    translate([0, Wo + 8, 0]) lid_print();
}

echo(str("Outer size: ", Lo, " x ", Wo, " x ", Ho, " mm"));
echo(str("Tray height: ", zs, " mm   Lid height: ", Ho - zs, " mm"));
