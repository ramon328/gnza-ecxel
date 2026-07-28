# Genera los 10 modelos ARMADOS como OBJ segun la planimetria HN:
#   barrera exterior 6M (L1-L3), barras interiores Hilux/L200/Colorado/POER
#   (HN-24/25/29/27), enganches Hilux/L200 (HN-57/121) y portarruedas
#   Tipo T / Kitcar / Estandar con cono (HN-20/12/25).
import math

FILLET_R = 250.0
SEG_CIRCLE = 40
SEG_ARC = 32

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


def sweep_tube(path, radius, cap=True):
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


def box(cx, cy, cz, sx, sy, sz, rx=0.0, ry=0.0, rz=0.0):
    """Caja centrada con rotaciones (radianes) aplicadas en orden x,y,z."""
    pts = []
    for dx in (-sx/2, sx/2):
        for dy in (-sy/2, sy/2):
            for dz in (-sz/2, sz/2):
                p = [dx, dy, dz]
                if rx:
                    p = rotate(p, [1, 0, 0], rx)
                if ry:
                    p = rotate(p, [0, 1, 0], ry)
                if rz:
                    p = rotate(p, [0, 0, 1], rz)
                pts.append((cx+p[0], cy+p[1], cz+p[2]))
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


def torus(c, R, r, axis='y', nseg=36, ntube=14):
    rows = []
    for i in range(nseg):
        a = 2*math.pi*i/nseg
        ring = []
        for k in range(ntube):
            b = 2*math.pi*k/ntube
            rr = R + r*math.cos(b)
            h = r*math.sin(b)
            if axis == 'y':
                p = (c[0]+rr*math.cos(a), c[1]+h, c[2]+rr*math.sin(a))
            elif axis == 'x':
                p = (c[0]+h, c[1]+rr*math.cos(a), c[2]+rr*math.sin(a))
            else:
                p = (c[0]+rr*math.cos(a), c[1]+rr*math.sin(a), c[2]+h)
            ring.append(add_vert(p))
        rows.append(ring)
    for i in range(nseg):
        r0, r1 = rows[i], rows[(i+1) % nseg]
        for k in range(ntube):
            k2 = (k+1) % ntube
            faces.append((r0[k], r1[k], r1[k2]))
            faces.append((r0[k], r1[k2], r0[k2]))


def rueda(c, axis='y', R=260, r=105, hub=165):
    """Neumatico de referencia con llanta."""
    start_group('neumatico')
    torus(c, R, r, axis=axis)
    start_group('llanta')
    d = r*0.38
    if axis == 'y':
        cylinder((c[0], c[1]-d, c[2]), (c[0], c[1]+d, c[2]), hub, nseg=28)
    elif axis == 'x':
        cylinder((c[0]-d, c[1], c[2]), (c[0]+d, c[1], c[2]), hub, nseg=28)
    else:
        cylinder((c[0], c[1], c[2]-d), (c[0], c[1], c[2]+d), hub, nseg=28)


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


# ============== BARRERA EXTERIOR 6M (L1-L3, tubo 3"x3) ==============
TUBE_R = 38.1
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
sweep_tube(fillet_path([list(p) for p in arco_pts]), TUBE_R)

for sx in (-1, 1):
    start_group('pata_%s' % ('izq' if sx < 0 else 'der'))
    pts = [
        (sx*260, -40, H-10),
        (sx*300, 90, H-60),
        (sx*640, 800, 240),
        (sx*660, 890, 120),
        (sx*660, 890, 0),
    ]
    sweep_tube(fillet_path([list(p) for p in pts]), TUBE_R)

start_group('placas_base')
for (px, py) in ((-430, 0), (430, 0), (-660, 890), (660, 890)):
    box(px, py, 4, 100, 180, 8)

# Vasos baliza cilindricos sobre los extremos del tramo superior (foto)
start_group('vasos_baliza')
for sx in (-1, 1):
    cylinder((sx*240, 0, H+36), (sx*240, 0, H+176), 64, nseg=32)

# Pletinas de montaje planas con perforaciones sobre el tubo superior (foto)
start_group('pletinas_montaje')
for px in (-160, 0, 160):
    box(px, 0, H+42, 100, 46, 5)

start_group('malla_luneta')


def malla(x0, x1, z0, z1, y, nx, nz, frame_r=8, wire_r=2.5, corner=45):
    ring = fillet_path([list(p) for p in [
        ((x0+x1)/2, y, z0),
        (x1, y, z0), (x1, y, z1), (x0, y, z1), (x0, y, z0),
        ((x0+x1)/2, y, z0),
    ]], r=corner)
    sweep_tube(ring, frame_r, cap=False)
    for i in range(1, nx):
        x = x0 + (x1-x0)*i/nx
        cylinder((x, y, z0), (x, y, z1), wire_r, nseg=10, cap=False)
    for j in range(1, nz):
        z = z0 + (z1-z0)*j/nz
        cylinder((x0, y, z), (x1, y, z), wire_r, nseg=10, cap=False)


malla(-545, 545, 360, 940, -15, 14, 8)
write_obj('models/barrera_armada.obj')


# ============== BARRAS INTERIORES (marco 1 1/2" SCH80 + placas + orejas) ==============
CANERIA_R = 24.15   # OD 48.3


def barra_interior(path_out, left_pts, right_pts, top_z, lean,
                   placa=(100, 200, 14), oreja=(50, 5, 170),
                   oreja_pos=None):
    """Marco asimetrico: left_pts sube desde el pie izquierdo hasta el corner
    superior izquierdo; right_pts baja desde el corner superior derecho al pie
    derecho. lean = desplazamiento -y del tubo en la parte superior."""
    reset()
    start_group('marco')
    pts = left_pts + right_pts
    path = fillet_path([list(p) + [] for p in pts], r=160)
    # inclinar hacia atras: shear en y proporcional a z
    for p in path:
        p[1] -= lean * (p[2] / top_z)
    sweep_tube(path, CANERIA_R)
    # Funda acolchada negra sobre el tramo superior (como en las fotos)
    pad = [p for p in path if p[2] >= top_z * 0.52]
    if len(pad) > 2:
        start_group('funda_acolchada')
        sweep_tube(pad, CANERIA_R * 1.75)
    start_group('placas_base')
    for pt in (left_pts[0], right_pts[-1]):
        box(pt[0], pt[1], 7, placa[0], placa[1], placa[2])
    start_group('orejas')
    for (px, py, pz, ang) in (oreja_pos or []):
        box(px, py - lean * (pz / top_z), pz, oreja[0], oreja[1], oreja[2], rz=ang)
    write_obj(path_out)


def p3(x, z):
    return (x, 0.0, z)


# HN-24 Toyota Hilux: base 1300, alto 1150, lado derecho quiebra en 879
barra_interior(
    'models/barra_int_hilux_armada.obj',
    [p3(-650, 0), p3(-650, 640), p3(-577, 872), p3(-330, 1150)],
    [p3(390, 1150), p3(650, 879), p3(650, 0)],
    1150, 120,
    placa=(100, 200, 14), oreja=(50, 5, 170),
    oreja_pos=[(-140, 25, 1150, 0), (530, 25, 1010, -0.7)],
)

# HN-25 Mitsubishi L200: ancho max 1350 en hombro 630, base 1270, alto 1160
barra_interior(
    'models/barra_int_l200_armada.obj',
    [p3(-635, 0), p3(-645, 300), p3(-675, 630), p3(-600, 905), p3(-360, 1160)],
    [p3(360, 1160), p3(600, 905), p3(675, 630), p3(645, 300), p3(635, 0)],
    1160, 115,
    placa=(90, 200, 14), oreja=(130, 5, 310),
    oreja_pos=[(-640, 25, 770, 0.2), (640, 25, 770, -0.2)],
)

# HN-29 Chevrolet Colorado: patas verticales 590, corona mas ancha (1330)
barra_interior(
    'models/barra_int_colorado_armada.obj',
    [p3(-660, 0), p3(-660, 590), p3(-682, 1000), p3(-455, 1160)],
    [p3(455, 1160), p3(682, 1000), p3(660, 590), p3(660, 0)],
    1160, 120,
    placa=(100, 200, 14), oreja=(130, 5, 310),
    oreja_pos=[(-500, 25, 1090, 0.5), (672, 25, 800, 0)],
)

# HN-27 GWM POER: base 1320, alto 1180, lado derecho quiebra en 985
barra_interior(
    'models/barra_int_poer_armada.obj',
    [p3(-660, 0), p3(-648, 710), p3(-580, 960), p3(-345, 1180)],
    [p3(400, 1180), p3(655, 985), p3(660, 0)],
    1180, 100,
    placa=(100, 200, 14), oreja=(50, 5, 160),
    oreja_pos=[(-200, 25, 1180, 0), (560, 25, 1070, -0.6)],
)


# ============== ENGANCHES (perfil 50x50x5 + alas + receptor hembra 2") ==============
def enganche(path_out, bar_len, ala, ala_tilt, ala_z):
    """Barra transversal con alas en los extremos y receptor central hembra."""
    reset()
    start_group('barra_transversal')
    box(0, 0, 0, 50, bar_len, 50)
    start_group('alas_laterales')
    aw, ah = ala          # largo (en y) y alto de la placa
    for sy in (-1, 1):
        box(0, sy*(bar_len/2 - aw/2 + 8), ala_z, 5, aw, ah, rx=sy*ala_tilt)
    start_group('placas_receptor')
    box(0, 0, -29, 180, 160, 8)          # placa 160x180x8 bajo la barra
    box(0, 0, 29, 105, 150, 8)           # placa superior 150x105
    start_group('receptor_hembra')
    box(35, 0, -62, 120, 62, 58)         # brazo hembra 6x2"
    box(98, 0, -62, 8, 66, 62)           # boca del receptor
    start_group('perno_seguro')
    cylinder((60, -40, -62), (60, 40, -62), 10, nseg=12)
    write_obj(path_out)


# HN-57 Toyota Hilux: barra 1030, alas 366x240x5 inclinadas
enganche('models/enganche_armado.obj', 1030, (366, 240), math.radians(35), 120)
# HN-121 Mitsubishi L200: barra 1150, alas verticales 310x360x5
enganche('models/enganche_l200_armado.obj', 1150, (310, 360), 0.0, 110)


# ============== PORTARRUEDAS TIPO T (HN-20) ==============
reset()
start_group('placa_anclaje_ajustable')
box(-168, 0, 400, 5, 120, 175)           # placa vertical con ranuras
box(-133, 0, 490, 75, 120, 5)            # pestana superior
start_group('brazo')
box(0, 0, 380, 330, 50, 50)              # perfil 50x50x2
start_group('poste')
box(45, 0, 190, 40, 40, 330)             # perfil 40x40 al piso
start_group('placa_anclaje_directo')
box(45, 0, 12, 160, 50, 5)
start_group('disco')
cylinder((167, 0, 380), (171, 0, 380), 67.5, nseg=32)
start_group('vastago')
cylinder((171, 0, 380), (300, 0, 380), 11, nseg=12)   # barra 3/4 hilo M22
box(310, 0, 380, 14, 90, 22)             # perno mariposa
rueda((262, 0, 380), axis='x')
write_obj('models/portarruedas_tipo_t_armado.obj')


# ============== PORTARRUEDAS TIPO KITCAR (HN-12, cuna de 2 marcos) ==============
reset()
MARCO_R = 16
start_group('base_angulos')
box(0, 0, 25, 750, 50, 50)
box(0, 520, 25, 750, 50, 50)
box(-350, 260, 25, 50, 470, 50)
box(350, 260, 25, 50, 470, 50)
start_group('marcos')
for y in (75, 445):
    pts = [
        (-375, y, 50), (-375, y, 520),
        (-170, y, 750), (200, y, 750),
        (375, y, 490), (375, y, 50),
    ]
    sweep_tube(fillet_path([list(p) for p in pts], r=110), MARCO_R)
start_group('pletinas')
box(-270, 260, 640, 60, 420, 5, ry=math.radians(-42))
box(290, 260, 625, 60, 420, 5, ry=math.radians(46))
start_group('discos')
for y in (75, 445):
    cylinder((-282, y, 648), (-278, y, 652), 50, nseg=24)
start_group('vastagos')
for y in (75, 445):
    p0 = (-300, y, 630)
    p1 = (-380, y, 720)
    cylinder(p0, p1, 8, nseg=10)
    box(-388, y, 729, 60, 16, 12, ry=math.radians(-45))
# Poste divisor central entre los dos marcos (foto vista superior)
start_group('poste_central')
cylinder((15, 260, 50), (15, 260, 748), 13, nseg=14)
rueda((0, 260, 400), axis='y', R=290, r=110, hub=180)
write_obj('models/portarruedas_kitcar_armado.obj')


# ============== PORTARRUEDAS ESTANDAR C/CONO (HN-25, bastidor 4 postes) ==============
reset()
POSTE_R = 14
ALTO = 950
start_group('postes')
for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
    pts = [
        (sx*150, sy*125, 10),
        (sx*150, sy*125, ALTO-180),
        (sx*95, sy*55, ALTO),
    ]
    sweep_tube(fillet_path([list(p) for p in pts], r=120), POSTE_R)
start_group('corona')
box(0, 0, ALTO+18, 280, 150, 36)
start_group('travesanos')
for z in (240, 520):
    for sy in (-1, 1):
        box(0, sy*125, z, 300, 40, 5, rz=0)
    box(0, 0, z-30, 40, 250, 5)
start_group('placas_perforadas')
for sx in (-1, 1):
    box(sx*140, 0, 240, 5, 220, 60)
start_group('vastago')
cylinder((0, 0, ALTO-320), (0, 0, ALTO+250), 9.5, nseg=12)  # hilo 3/4
start_group('disco')
cylinder((0, 0, ALTO-318), (0, 0, ALTO-314), 75, nseg=32)
start_group('mariposa')
box(0, 0, ALTO+260, 110, 16, 24, rz=math.radians(25))
rueda((0, 0, ALTO+142), axis='z')
write_obj('models/portarruedas_mitta_armado.obj')
