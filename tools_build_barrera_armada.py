# Builds an assembled "Barrera antivuelco 6M" OBJ from the drawing dimensions
# (L1/L3 planimetria): arco + 2 patas (tube 3" = 76.2mm) + 4 placas base 180x100x8
# + 2 discos baliza D135.
import math

TUBE_R = 38.1
FILLET_R = 250.0
SEG_CIRCLE = 28
SEG_ARC = 12

verts = []
faces = []


def add_vert(p):
    verts.append(p)
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
    """Polyline -> point list with arc fillets at interior vertices."""
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
            pt = add(c, rotate(mul(n0, -rr), axis, th))
            path.append(pt)
    path.append(points[-1])
    return path


def sweep_tube(path, radius=TUBE_R, cap=True):
    """Sweep circle along path with parallel-transport frames."""
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
                if flip:
                    faces.append((cidx, ring[k2], ring[k]))
                else:
                    faces.append((cidx, ring[k], ring[k2]))


def box(cx, cy, cz, sx, sy, sz):
    x0, x1 = cx - sx/2, cx + sx/2
    y0, y1 = cy - sy/2, cy + sy/2
    z0, z1 = cz - sz/2, cz + sz/2
    i = [add_vert(p) for p in [
        (x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
        (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]]
    quads = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(2,3,7,6),(1,2,6,5),(3,0,4,7)]
    for q in quads:
        faces.append((i[q[0]], i[q[1]], i[q[2]]))
        faces.append((i[q[0]], i[q[2]], i[q[3]]))


def disc(cx, cy, cz, r, th):
    n = 32
    top, bot = [], []
    for k in range(n):
        a = 2*math.pi*k/n
        dx, dy = r*math.cos(a), r*math.sin(a)
        top.append(add_vert((cx+dx, cy+dy, cz+th/2)))
        bot.append(add_vert((cx+dx, cy+dy, cz-th/2)))
    ct = add_vert((cx, cy, cz+th/2))
    cb = add_vert((cx, cy, cz-th/2))
    for k in range(n):
        k2 = (k+1) % n
        faces.append((ct, top[k], top[k2]))
        faces.append((cb, bot[k2], bot[k]))
        faces.append((top[k], bot[k], bot[k2]))
        faces.append((top[k], bot[k2], top[k2]))


groups = []


def start_group(name):
    groups.append((name, len(faces)))


# ---------------- ARCO (rear hoop, plane y=0) ----------------
H = 1033.0
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
start_group('arco')
sweep_tube(fillet_path([list(p) for p in arco_pts]))

# ---------------- PATAS ----------------
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

# ---------------- PLACAS BASE 180x100x8 ----------------
start_group('placas_base')
for (px, py) in ((-430, 0), (430, 0), (-660, 890), (660, 890)):
    box(px, py, 4, 100, 180, 8)

# ---------------- DISCOS BALIZA D135 ----------------
start_group('discos_baliza')
for sx in (-1, 1):
    disc(sx*470, 450, 645, 67.5, 4)

# ---------------- write OBJ ----------------
out = ['v %.2f %.2f %.2f' % tuple(v) for v in verts]
gi = 0
lines_faces = []
for fi, f in enumerate(faces):
    while gi < len(groups) and groups[gi][1] == fi:
        lines_faces.append('o ' + groups[gi][0])
        gi += 1
    lines_faces.append('f %d %d %d' % f)
with open('/Users/macbookramon/conductor/workspaces/gonzalo/rabat/models/barrera_armada.obj', 'w') as fh:
    fh.write('\n'.join(out) + '\n' + '\n'.join(lines_faces) + '\n')
print('verts', len(verts), 'faces', len(faces), 'groups', len(groups))
