# Genera los modelos ARMADOS como OBJ:
#  - barrera_armada.obj: arco + patas + placas base + discos baliza + pertigas
#    + focos + anclaje + mallas luneta (lista de piezas de la lamina L1)
#  - enganche_armado.obj: placas laterales + barra 50x50 + soportes + bola,
#    con las dimensiones medidas de las piezas del DWG.
# Dimensiones planimetria: tubo 3" (D76.2) x 3mm, curvas R250, alto 1033.
import math

TUBE_R = 38.1
FILLET_R = 250.0
SEG_CIRCLE = 28
SEG_ARC = 12

verts = []
faces = []
groups = []


def start_group(name):
    groups.append((name, len(faces)))


def add_vert(p):
    verts.append(tuple(p))
    return len(verts)


def norm(v):
    l = math.sqrt(sum(c * c for c in v)) or 1.0
    return [c / l for c in v]


def sub(a, b): return [a[i] - b[i] for i in range(3)]
def add(a, b): return [a[i] + b[i] for i in range(3)]
def mul(a, s): return [c * s for c in a]
def dot(a, b): return sum(a[i] * b[i] for i in range(3))
def cross(a, b):
    return [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
def dist(a, b): return math.sqrt(sum((a[i]-b[i])**2 for i in range(3)))


def rotate(v, axis, th):
    c, s = math.cos(th), math.sin(th)
    return add(add(mul(v, c), mul(cross(axis, v), s)), mul(axis, dot(axis, v) * (1 - c)))


def fillet_path(points, r=FILLET_R):
    path = [points[0]]
    for i in range(1, len(points) - 1):
        p0, p1, p2 = points[i-1], points[i], points[i+1]
        d0, d1 = norm(sub(p1, p0)), norm(sub(p2, p1))
        cosang = max(-1.0, min(1.0, dot(d0, d1)))
        ang = math.acos(cosang)
        if ang < 1e-3:
            path.append(p1)
            continue
        t = r * math.tan(ang / 2)
        lmax = min(dist(p0, p1), dist(p1, p2)) * 0.49
        rr = r
        if t > lmax:
            rr = lmax / math.tan(ang / 2)
            t = lmax
        a = add(p1, mul(d0, -t))
        axis = norm(cross(d0, d1))
        n0 = norm(cross(axis, d0))
        c = add(a, mul(n0, rr))
        for k in range(1, SEG_ARC + 1):
            th = ang * k / SEG_ARC
            path.append(add(c, rotate(mul(n0, -rr), axis, th)))
    path.append(points[-1])
    return path


def sweep_tube(path, radius=TUBE_R, cap=True):
    t0 = norm(sub(path[1], path[0]))
    up = [0, 0, 1] if abs(t0[2]) < 0.9 else [1, 0, 0]
    n = norm(cross(t0, up))
    b = norm(cross(t0, n))
    rings = []
    prev_t = t0
    for i, p in enumerate(path):
        if 0 < i < len(path) - 1:
            t = norm(sub(path[i+1], path[i-1]))
        elif i == 0:
            t = t0
        else:
            t = norm(sub(path[i], path[i-1]))
        axis = cross(prev_t, t)
        s = math.sqrt(dot(axis, axis))
        if s > 1e-9:
            axis = [a/s for a in axis]
            th = math.atan2(s, max(-1.0, min(1.0, dot(prev_t, t))))
            n = rotate(n, axis, th)
            b = rotate(b, axis, th)
        prev_t = t
        ring = []
        for k in range(SEG_CIRCLE):
            a = 2 * math.pi * k / SEG_CIRCLE
            offs = add(mul(n, radius * math.cos(a)), mul(b, radius * math.sin(a)))
            ring.append(add_vert(add(p, offs)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i+1]
        for k in range(SEG_CIRCLE):
            k2 = (k + 1) % SEG_CIRCLE
            faces.append((r0[k], r1[k], r1[k2]))
            faces.append((r0[k], r1[k2], r0[k2]))
    if cap:
        for ring, p, flip in ((rings[0], path[0], True), (rings[-1], path[-1], False)):
            cidx = add_vert(p)
            for k in range(SEG_CIRCLE):
                k2 = (k + 1) % SEG_CIRCLE
                faces.append((cidx, ring[k2], ring[k]) if flip else (cidx, ring[k], ring[k2]))


def box(cx, cy, cz, sx, sy, sz, rot_z=0.0):
    pts = []
    for dx in (-sx/2, sx/2):
        for dy in (-sy/2, sy/2):
            for dz in (-sz/2, sz/2):
                x = dx*math.cos(rot_z) - dy*math.sin(rot_z)
                y = dx*math.sin(rot_z) + dy*math.cos(rot_z)
                pts.append((cx+x, cy+y, cz+dz))
    # pts order: (-,-,-),(-,-,+),(-,+,-),(-,+,+),(+,-,-),(+,-,+),(+,+,-),(+,+,+)
    i = [add_vert(p) for p in pts]
    quads = [(0,2,6,4),(1,5,7,3),(0,4,5,1),(2,3,7,6),(0,1,3,2),(4,6,7,5)]
    for q in quads:
        faces.append((i[q[0]], i[q[1]], i[q[2]]))
        faces.append((i[q[0]], i[q[2]], i[q[3]]))


def cylinder(p0, p1, r, nseg=24, cap=True):
    axis = norm(sub(p1, p0))
    up = [0, 0, 1] if abs(axis[2]) < 0.9 else [1, 0, 0]
    n = norm(cross(axis, up))
    b = norm(cross(axis, n))
    r0, r1 = [], []
    for k in range(nseg):
        a = 2*math.pi*k/nseg
        offs = add(mul(n, r*math.cos(a)), mul(b, r*math.sin(a)))
        r0.append(add_vert(add(p0, offs)))
        r1.append(add_vert(add(p1, offs)))
    for k in range(nseg):
        k2 = (k+1) % nseg
        faces.append((r0[k], r1[k], r1[k2]))
        faces.append((r0[k], r1[k2], r0[k2]))
    if cap:
        c0, c1 = add_vert(p0), add_vert(p1)
        for k in range(nseg):
            k2 = (k+1) % nseg
            faces.append((c0, r0[k2], r0[k]))
            faces.append((c1, r1[k], r1[k2]))


def sphere(c, r, nseg=20):
    rows = []
    for i in range(nseg+1):
        phi = math.pi * i / nseg
        ring = []
        for k in range(nseg):
            th = 2*math.pi*k/nseg
            ring.append(add_vert((c[0]+r*math.sin(phi)*math.cos(th),
                                  c[1]+r*math.sin(phi)*math.sin(th),
                                  c[2]+r*math.cos(phi))))
        rows.append(ring)
    for i in range(nseg):
        for k in range(nseg):
            k2 = (k+1) % nseg
            a, b2, c2, d = rows[i][k], rows[i+1][k], rows[i+1][k2], rows[i][k2]
            faces.append((a, b2, c2))
            faces.append((a, c2, d))


def write_obj(path):
    out = ['v %.2f %.2f %.2f' % v for v in verts]
    gi = 0
    fl = []
    for fi, f in enumerate(faces):
        while gi < len(groups) and groups[gi][1] == fi:
            fl.append('o ' + groups[gi][0])
            gi += 1
        fl.append('f %d %d %d' % f)
    with open(path, 'w') as fh:
        fh.write('\n'.join(out) + '\n' + '\n'.join(fl) + '\n')
    print(path, 'verts', len(verts), 'faces', len(faces), 'groups', len(groups))


def reset():
    global verts, faces, groups
    verts, faces, groups = [], [], []


# ================= BARRERA ANTIVUELCO 6M =================
H = 1033.0
start_group('arco')
arco_pts = [
    (-430, 0, 0), (-430, 0, 150),
    (-702, 0, 580),
    (-560, 0, 920),
    (-260, 0, H),
    (260, 0, H),
    (560, 0, 920),
    (702, 0, 580),
    (430, 0, 150), (430, 0, 0),
]
sweep_tube(fillet_path([list(p) for p in arco_pts]))

for sx in (-1, 1):
    start_group('pata_%s' % ('izq' if sx < 0 else 'der'))
    pts = [
        (sx*260, -40, H-10),
        (sx*300, 90, H-60),
        (sx*640, 800, 240),
        (sx*660, 890, 120),
        (sx*660, 890, 0),
    ]
    sweep_tube(fillet_path([list(p) for p in pts]))

start_group('placas_base')
for (px, py) in ((-430, 0), (430, 0), (-660, 890), (660, 890)):
    box(px, py, 4, 100, 180, 8)

# Discos baliza D135 con vastago 138 (sobre las patas)
start_group('discos_baliza')
for sx in (-1, 1):
    p_low = (sx*470, 430, 660)
    p_top = (sx*470, 430, 795)
    cylinder(p_low, p_top, 8)          # vastago 138
    # disco horizontal
    c = (sx*470, 430, 800)
    cylinder((c[0], c[1], c[2]-2), (c[0], c[1], c[2]+2), 67.5, nseg=32)

# Pertigas: soporte + tubo vertical en los codos del arco
start_group('pertigas')
for sx in (-1, 1):
    base = (sx*690, 0, 640)
    box(base[0], base[1], base[2], 60, 60, 90)
    cylinder((base[0], base[1], base[2]+45), (base[0], base[1], base[2]+445), 12)

# Focos sobre el tramo recto superior del arco
start_group('focos')
for sx in (-1, 1):
    cx = sx*150
    box(cx, -20, H+55, 90, 40, 60)
    cylinder((cx, -40, H+55), (cx, -70, H+55), 35, nseg=24)

# Anclaje central (placa superior)
start_group('anclaje')
box(0, 40, H-40, 410, 180, 8, rot_z=0)

# Mallas luneta: 2 paneles enrejados entre el arco y la vertical
start_group('malla_luneta_1')


def malla(x0, x1, z0, z1, y, nx, nz, r=6):
    for i in range(nx+1):
        x = x0 + (x1-x0)*i/nx
        cylinder((x, y, z0), (x, y, z1), r, nseg=8, cap=False)
    for j in range(nz+1):
        z = z0 + (z1-z0)*j/nz
        cylinder((x0, y, z), (x1, y, z), r, nseg=8, cap=False)


malla(-560, -40, 350, 950, -15, 5, 6)
start_group('malla_luneta_2')
malla(40, 560, 350, 950, -15, 5, 6)

write_obj('models/barrera_armada.obj')

# ================= ENGANCHE HILUX =================
# Dimensiones reales de las piezas del DWG (en mm):
#  placas laterales 366x240x5, separadas 1035; barra 50x50x1040;
#  soporte central 195x180x73; placa bola 105x150x20; bola D75 sobre cuello.
reset()

start_group('placas_laterales')
for sy in (-1, 1):
    box(0, sy*517, 0, 366, 5, 240)

start_group('barra_transversal')
box(0, 0, -50, 50, 1040, 50)

start_group('placas_extremo')
for sy in (-1, 1):
    box(0, sy*522, -50, 130, 4, 100)

start_group('soporte_central')
box(90, 0, -55, 195, 180, 73)

start_group('placa_bola')
box(180, 0, -45, 105, 150, 20)

start_group('bola')
cylinder((205, 0, -35), (205, 0, 25), 15)   # cuello
sphere((205, 0, 45), 37.5)

write_obj('models/enganche_armado.obj')
