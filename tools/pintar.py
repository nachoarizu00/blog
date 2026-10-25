"""Genera las texturas de pintura de CUALQUIERA (public/arte/*.webp).
Pinceladas con cerdas, lavados translúcidos, lápiz, gestos negros y puntos.
Uso: python3 tools/pintar.py
"""
import math, random, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), '..', 'public', 'arte')
os.makedirs(OUT, exist_ok=True)

CELESTE = (91, 188, 250)
CELESTE_CLARO = (150, 214, 253)
AZUL = (56, 160, 238)
AZUL_PROFUNDO = (40, 130, 215)
CORAL = (242, 95, 76)
ROSA = (242, 154, 150)
OCRE = (190, 164, 118)
TIERRA = (142, 112, 74)
NEGRO = (10, 10, 11)
LAPIZ = (90, 94, 104)


def curva(puntos, n=120):
    """Catmull-Rom sobre una lista de puntos."""
    p = [puntos[0]] + list(puntos) + [puntos[-1]]
    res = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for t in np.linspace(0, 1, max(8, n // max(1, len(puntos) - 1)), endpoint=False):
            t2, t3 = t * t, t * t * t
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            res.append((x, y))
    res.append(puntos[-1])
    return np.array(res)


def normales(c):
    d = np.gradient(c, axis=0)
    n = np.stack([-d[:, 1], d[:, 0]], axis=1)
    l = np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    return n / l


def ruido_suave(n, escala, rng):
    k = max(2, int(n / escala))
    base = rng.normal(0, 1, k + 3)
    xs = np.linspace(0, k, n)
    return np.interp(xs, np.arange(len(base)), base)


_GRANO = {}


def grano(size, seed=99):
    """Tooth del papel: ruido de dos escalas, para que la pintura seca se 'coma'."""
    if size not in _GRANO:
        r = np.random.default_rng(seed)
        w, h = size
        fino = Image.fromarray((r.random((h, w)) * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(1.1))
        medio = Image.fromarray((r.random((h // 5 + 1, w // 5 + 1)) * 255).astype('uint8')).resize(size, Image.BICUBIC).filter(ImageFilter.GaussianBlur(2))
        f = np.array(fino, dtype=float) / 255
        m = np.array(medio, dtype=float) / 255
        f = (f - f.min()) / (f.max() - f.min())
        m = (m - m.min()) / (m.max() - m.min())
        _GRANO[size] = 0.6 * f + 0.4 * m
    return _GRANO[size]


def comer(capa_img, seco, rng):
    """Resta pintura donde el grano del papel es alto, más cuanto más seco."""
    a = np.array(capa_img)
    g = grano(capa_img.size)
    mask = 1 - (0.22 + 0.4 * seco) * np.clip((g - 0.42) * 3.2, 0, 1)
    a[..., 3] = (a[..., 3] * np.clip(mask, 0, 1)).astype('uint8')
    return Image.fromarray(a, 'RGBA')


def pincelada(capa, puntos, ancho, color, rng, alfa=0.85, cerdas=None, seco=0.5, cuerpo=0.35, variacion=34):
    """Pincelada hecha de cerdas gruesas sobre un cuerpo translúcido, con el borde seco."""
    c = curva(puntos)
    nor = normales(c)
    n = len(c)
    t = np.linspace(0, 1, n)
    perfil = np.clip(np.minimum(t / 0.07, (1 - t) / 0.16), 0, 1) ** 0.45
    perfil = perfil * (0.88 + 0.12 * ruido_suave(n, 30, rng))
    cerdas = cerdas or int(max(14, ancho / 2.8))

    hoja = Image.new('RGBA', capa.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(hoja)
    wob = ruido_suave(n, 70, rng) * ancho * 0.06
    for i in range(0, n, 2):
        r = ancho * 0.5 * perfil[i] * 0.95
        x, y = c[i] + nor[i] * wob[i]
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*color, int(255 * alfa * cuerpo)))
    hoja = hoja.filter(ImageFilter.GaussianBlur(max(1.5, ancho * 0.025)))
    d = ImageDraw.Draw(hoja)

    for b in range(cerdas):
        u = b / (cerdas - 1) - 0.5
        borde = abs(u) * 2
        fin = 1 - seco * (borde ** 1.4) * rng.uniform(0.2, 1.1) - rng.uniform(0, 0.1)
        ini = rng.uniform(0, 0.04) + 0.05 * borde * rng.uniform(0, 1)
        i0, i1 = int(ini * n), int(max(fin, 0.12) * n)
        if i1 - i0 < 4:
            continue
        w = max(2, int(ancho / cerdas * rng.uniform(2.0, 4.0)))
        dj = rng.integers(-variacion, variacion + 1)
        j = [dj + int(rng.integers(-5, 6)) for _ in range(3)]
        col = tuple(int(np.clip(color[k] + j[k], 0, 255)) for k in range(3))
        deriva = ruido_suave(n, 80, rng) * ancho * 0.035
        a0 = rng.uniform(0.62, 1.0) * alfa
        idx = np.arange(i0, i1)
        off = u * ancho * perfil[idx] + deriva[idx]
        pts = [tuple(c[i] + nor[i] * o) for i, o in zip(idx, off)]
        tramo = max(5, len(pts) // 18)
        for s0 in range(0, len(pts) - 1, tramo):
            f = s0 / max(1, len(pts))
            al = a0 * (1 - 0.7 * max(0, f - 0.6) / 0.4) * rng.uniform(0.8, 1.0)
            d.line(pts[s0:s0 + tramo + 1], fill=(*col, int(255 * max(0.06, al))), width=w, joint='curve')
    hoja = comer(hoja, seco, rng)
    capa.alpha_composite(hoja)


def rascado(capa, caja, cantidad, ancho, color, rng, angulo=-25, largo=(120, 320), alfa=0.8, seco=0.8):
    """Muchas pinceladas cortas y nerviosas que se cruzan, como la pintura que se frota."""
    x0, y0, x1, y1 = caja
    for _ in range(cantidad):
        cx, cy = rng.uniform(x0, x1), rng.uniform(y0, y1)
        a = math.radians(angulo + rng.normal(0, 14))
        L = rng.uniform(*largo)
        dx, dy = math.cos(a) * L / 2, math.sin(a) * L / 2
        q = [(cx - dx, cy - dy), (cx + rng.normal(0, 14), cy + rng.normal(0, 14)), (cx + dx, cy + dy)]
        pincelada(capa, q, ancho * rng.uniform(0.7, 1.3), color, rng, alfa * rng.uniform(0.6, 1), seco=seco, cuerpo=0.25)


def lavado(capa, centro, radios, color, rng, alfa=0.3, lobulos=0):
    """Mancha acuosa suave, con el borde un poco más cargado y moteada por dentro."""
    img = Image.new('L', capa.size, 0)
    d = ImageDraw.Draw(img)
    f1, f2, f3 = rng.uniform(0, 6, 3)
    pts = []
    for a in np.linspace(0, 2 * math.pi, 160, endpoint=False):
        r = 1 + 0.16 * math.sin(2 * a + f1) + 0.10 * math.sin(3 * a + f2) + 0.05 * math.sin(5 * a + f3)
        pts.append((centro[0] + math.cos(a) * radios[0] * r, centro[1] + math.sin(a) * radios[1] * r))
    d.polygon(pts, fill=255)
    sig = min(radios) * 0.07
    cuerpo = np.array(img.filter(ImageFilter.GaussianBlur(sig)), dtype=float) / 255
    interior = np.array(img.filter(ImageFilter.GaussianBlur(sig * 3.5)), dtype=float) / 255
    borde = np.clip(cuerpo - interior * 0.85, 0, 1)
    h, w = capa.size[1], capa.size[0]
    mott = np.array(Image.fromarray((rng.random((h // 36 + 2, w // 36 + 2)) * 255).astype('uint8')).resize(capa.size, Image.BICUBIC).filter(ImageFilter.GaussianBlur(14)), dtype=float) / 255
    mott = (mott - mott.min()) / (mott.max() - mott.min() + 1e-9)
    a = (cuerpo * alfa * (0.55 + 0.9 * mott) + borde * alfa * 0.8)
    lay = np.zeros((h, w, 4), dtype='uint8')
    lay[..., 0], lay[..., 1], lay[..., 2] = color
    lay[..., 3] = (np.clip(a, 0, 1) * 255).astype('uint8')
    capa.alpha_composite(Image.fromarray(lay, 'RGBA'))


def lapiz(capa, inicio, pasos, paso, rng, giro=0.9, color=LAPIZ, alfa=0.6, ancho=3, pasadas=2):
    """Garabato a lápiz: nudos densos de bucles, no hilos largos."""
    d = ImageDraw.Draw(capa)
    for _ in range(pasadas):
        x, y = inicio[0] + rng.normal(0, 10), inicio[1] + rng.normal(0, 10)
        ang = rng.uniform(0, 2 * math.pi)
        vel = 0
        pts = []
        for _ in range(pasos):
            vel = vel * 0.78 + rng.normal(0, giro)
            ang += vel * 0.34
            x += math.cos(ang) * paso
            y += math.sin(ang) * paso * 0.85
            pts.append((x, y))
        d.line(pts, fill=(*color, int(255 * alfa)), width=ancho, joint='curve')


def gesto(capa, puntos, ancho, rng, color=NEGRO, alfa=0.92, presion=None):
    """Trazo caligráfico negro de grosor variable."""
    c = curva(puntos, 220)
    n = len(c)
    d = ImageDraw.Draw(capa)
    t = np.linspace(0, 1, n)
    pres = presion(t) if presion else (np.sin(np.pi * t) ** 0.6)
    pres = pres * (0.8 + 0.2 * ruido_suave(n, 20, rng))
    for i in range(n):
        r = max(0.8, ancho * 0.5 * pres[i])
        x, y = c[i]
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*color, int(255 * alfa)))


def puntos(capa, centro, filas, cols, sep, radio, rng, colores):
    d = ImageDraw.Draw(capa)
    for i in range(filas):
        for j in range(cols):
            if rng.random() < 0.12:
                continue
            x = centro[0] + j * sep + rng.normal(0, sep * 0.12)
            y = centro[1] + i * sep + rng.normal(0, sep * 0.12) + math.sin(j * 0.9) * sep * 0.25
            r = radio * rng.uniform(0.7, 1.3)
            col = colores[rng.integers(len(colores))]
            d.ellipse([x - r, y - r, x + r, y + r], fill=(*col, 235))


def goteo(capa, x, y, largo, ancho, color, rng, alfa=0.75):
    d = ImageDraw.Draw(capa)
    xs = x + np.cumsum(rng.normal(0, 0.4, int(largo)))
    for k in range(int(largo)):
        d.ellipse([xs[k] - ancho / 2, y + k - ancho / 2, xs[k] + ancho / 2, y + k + ancho / 2], fill=(*color, int(255 * alfa)))
    r = ancho * 0.9
    d.ellipse([xs[-1] - r, y + largo - r, xs[-1] + r, y + largo + r], fill=(*color, int(255 * alfa)))


def salpicado(capa, caja, cantidad, color, rng, rmax=5):
    d = ImageDraw.Draw(capa)
    x0, y0, x1, y1 = caja
    for _ in range(cantidad):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = rng.exponential(rmax * 0.4) + 0.8
        d.ellipse([x - r, y - r, x + r, y + r], fill=(*color, int(rng.uniform(120, 230))))


def difuminar_bordes(capa, margen):
    w, h = capa.size
    m = np.ones((h, w))
    ramp_x = np.minimum(np.linspace(0, 1, w) * w / margen, np.linspace(1, 0, w) * w / margen).clip(0, 1)
    ramp_y = np.minimum(np.linspace(0, 1, h) * h / margen, np.linspace(1, 0, h) * h / margen).clip(0, 1)
    m = np.outer(ramp_y, ramp_x) ** 0.8
    a = np.array(capa)
    a[..., 3] = (a[..., 3] * m).astype('uint8')
    return Image.fromarray(a, 'RGBA')


def guardar(capa, nombre, calidad=82, margen=60):
    capa = difuminar_bordes(capa, margen)
    capa.save(os.path.join(OUT, nombre), 'WEBP', quality=calidad, method=6)
    print(nombre, capa.size, os.path.getsize(os.path.join(OUT, nombre)) // 1024, 'KB')


def lienzo(w, h):
    return Image.new('RGBA', (w, h), (0, 0, 0, 0))


# ─────────────── composiciones ───────────────

def circulo(c, cx, cy, r, color, rng, ancho=26, alfa=0.9):
    pts = [(cx + r * math.cos(a), cy + r * 0.88 * math.sin(a)) for a in np.linspace(0.4, 2 * math.pi + 0.35, 9)]
    pincelada(c, pts, ancho, color, rng, alfa, seco=0.35, cerdas=9, cuerpo=0.5)


def hero(seed=3):
    rng = np.random.default_rng(seed)
    W, H = 2800, 900
    c = lienzo(W, H)
    lavado(c, (1300, 470), (1150, 300), CELESTE_CLARO, rng, 0.34)
    lavado(c, (2150, 430), (560, 330), CELESTE, rng, 0.26)
    lavado(c, (520, 540), (460, 230), ROSA, rng, 0.3)
    rascado(c, (1500, 220, 2500, 560), 26, 70, CELESTE, rng, angulo=-35, alfa=0.7)
    pincelada(c, [(60, 520), (620, 400), (1300, 500), (2000, 400), (2740, 480)], 280, CELESTE, rng, 0.92, seco=0.85)
    pincelada(c, [(1000, 120), (1180, 380), (1330, 650), (1500, 800)], 110, AZUL, rng, 0.85, seco=0.8)
    pincelada(c, [(220, 640), (900, 590), (1700, 650), (2300, 590)], 120, AZUL, rng, 0.75, seco=0.85)
    pincelada(c, [(160, 720), (560, 660), (940, 740)], 80, CORAL, rng, 0.9, seco=0.75)
    pincelada(c, [(1850, 720), (2250, 670), (2660, 740)], 100, OCRE, rng, 0.9, seco=0.9)
    rascado(c, (300, 180, 760, 420), 12, 46, CORAL, rng, angulo=-60, largo=(80, 200), alfa=0.85)
    circulo(c, 1980, 250, 90, CORAL, rng)
    circulo(c, 600, 300, 60, CORAL, rng, 20)
    for x, ancho in [(700, 6), (1580, 5), (2250, 7), (1050, 5)]:
        goteo(c, x, 620, rng.integers(60, 190), ancho, AZUL if x != 1580 else CELESTE, rng)
    puntos(c, (2350, 120), 4, 6, 34, 8, rng, [NEGRO, CORAL, AZUL_PROFUNDO])
    gesto(c, [(1450, 130), (1380, 70), (1330, 150), (1420, 190), (1520, 120), (1600, 60), (1700, 140)], 15, rng)
    gesto(c, [(2480, 610), (2540, 560), (2600, 650), (2690, 590)], 13, rng)
    gesto(c, [(150, 190), (220, 140), (190, 250), (310, 200)], 12, rng)
    salpicado(c, (200, 100, 2600, 850), 150, AZUL, rng, 7)
    salpicado(c, (200, 100, 2600, 850), 50, CORAL, rng, 6)
    guardar(c, 'encabezado.webp', margen=140)


def cuadro_a(seed=11):
    rng = np.random.default_rng(seed)
    W = H = 1500
    c = lienzo(W, H)
    lavado(c, (720, 700), (600, 620), CELESTE_CLARO, rng, 0.3)
    lavado(c, (470, 960), (380, 300), ROSA, rng, 0.4)
    lavado(c, (1040, 420), (380, 320), CELESTE, rng, 0.3)
    rascado(c, (200, 300, 1300, 600), 40, 60, CELESTE, rng, angulo=-30, alfa=0.8)
    rascado(c, (250, 780, 900, 1000), 30, 60, CORAL, rng, angulo=-20, alfa=0.85)
    rascado(c, (300, 1050, 1250, 1250), 24, 56, AZUL, rng, angulo=-15, alfa=0.8)
    pincelada(c, [(880, 150), (940, 420), (900, 720), (960, 1030)], 90, OCRE, rng, 0.85, seco=0.85)
    pincelada(c, [(500, 650), (840, 600), (1200, 700)], 100, ROSA, rng, 0.85, seco=0.8)
    circulo(c, 420, 560, 70, CORAL, rng, 22)
    puntos(c, (610, 430), 4, 6, 30, 7, rng, [NEGRO, CORAL])
    gesto(c, [(300, 250), (240, 330), (330, 420), (400, 300), (330, 230)], 14, rng)
    gesto(c, [(1050, 300), (1130, 380), (1090, 520), (1180, 560)], 13, rng)
    gesto(c, [(380, 1000), (430, 920), (480, 1050), (560, 960)], 12, rng)
    goteo(c, 760, 900, 220, 6, CELESTE, rng)
    goteo(c, 540, 1160, 160, 6, CORAL, rng)
    salpicado(c, (150, 150, 1350, 1350), 140, AZUL, rng, 7)
    guardar(c, 'cuadro-a.webp', margen=180)


def cuadro_b(seed=21):
    rng = np.random.default_rng(seed)
    W, H = 1800, 1200
    c = lienzo(W, H)
    lavado(c, (900, 560), (800, 420), CELESTE_CLARO, rng, 0.32)
    lavado(c, (1320, 700), (380, 280), CELESTE, rng, 0.34)
    rascado(c, (900, 250, 1650, 560), 36, 64, CELESTE, rng, angulo=-40, alfa=0.8)
    pincelada(c, [(160, 400), (560, 280), (1000, 380), (1500, 300)], 180, CELESTE, rng, 0.9, seco=0.85)
    pincelada(c, [(560, 180), (620, 520), (580, 860)], 140, AZUL_PROFUNDO, rng, 0.85, seco=0.8)
    pincelada(c, [(240, 820), (700, 740), (1250, 830), (1620, 760)], 130, OCRE, rng, 0.85, seco=0.9)
    pincelada(c, [(300, 980), (700, 930), (1120, 1000)], 70, CORAL, rng, 0.9, seco=0.8)
    circulo(c, 1130, 640, 125, CORAL, rng, 28)
    circulo(c, 320, 560, 85, CORAL, rng, 24)
    puntos(c, (1380, 420), 5, 5, 28, 7, rng, [CELESTE_CLARO, AZUL, NEGRO])
    gesto(c, [(1000, 180), (1040, 260), (980, 330), (1090, 300), (1180, 220)], 13, rng)
    gesto(c, [(240, 220), (310, 180), (290, 280), (390, 240)], 12, rng)
    salpicado(c, (150, 150, 1650, 1050), 130, AZUL, rng, 7)
    guardar(c, 'cuadro-b.webp', margen=160)


def trazo(nombre, color, ancho, largo, seed, seco=0.7, extra=None):
    rng = np.random.default_rng(seed)
    W, H = largo, int(ancho * 3)
    c = lienzo(W, H)
    m = H / 2
    pincelada(c, [(70, m + 10), (W * 0.3, m - 24), (W * 0.62, m + 30), (W - 70, m - 10)], ancho, color, rng, 0.9, seco=seco)
    if extra:
        pincelada(c, [(W * 0.15, m + ancho * 0.32), (W * 0.5, m + ancho * 0.22), (W * 0.85, m + ancho * 0.34)], ancho * 0.35, extra, rng, 0.7, seco=0.8)
    salpicado(c, (W * 0.1, m - ancho, W * 0.9, m + ancho * 1.1), 30, color, rng, 4)
    guardar(c, nombre, margen=40)


def gestos(seed=5):
    rng = np.random.default_rng(seed)
    W, H = 1300, 560
    c = lienzo(W, H)
    gesto(c, [(120, 120), (60, 240), (140, 400), (260, 320), (190, 200), (320, 130), (480, 290), (560, 180)], 13, rng)
    gesto(c, [(640, 110), (700, 210), (660, 320), (800, 340), (880, 240), (990, 160), (1100, 260)], 11, rng)
    gesto(c, [(300, 470), (370, 410), (350, 510), (470, 450)], 9, rng)
    puntos(c, (900, 380), 3, 6, 30, 6, rng, [NEGRO, CORAL])
    guardar(c, 'gestos.webp', margen=30)


def diagonal(seed=7):
    """Una sola pincelada celeste, en diagonal, suelta sobre el papel."""
    rng = np.random.default_rng(seed)
    W, H = 2400, 1100
    c = lienzo(W, H)
    pincelada(c, [(120, 930), (700, 760), (1300, 560), (1900, 330), (2290, 190)], 230, CELESTE, rng, 0.95, seco=0.9, cuerpo=0.4)
    pincelada(c, [(480, 900), (1100, 700), (1700, 500), (2050, 380)], 70, AZUL, rng, 0.8, seco=0.9, cuerpo=0.2)
    goteo(c, 760, 840, 120, 5, CELESTE, rng, 0.8)
    salpicado(c, (300, 300, 2200, 1000), 26, CELESTE, rng, 6)
    guardar(c, 'diagonal.webp', margen=40)


def garabatos_a(seed=2):
    rng = np.random.default_rng(seed)
    c = lienzo(1000, 700)
    gesto(c, [(140, 120), (90, 220), (170, 320), (260, 230), (200, 140), (330, 120), (450, 230)], 14, rng)
    gesto(c, [(640, 130), (700, 210), (660, 300), (790, 280)], 12, rng)
    guardar(c, 'garabatos-a.webp', margen=30)


def garabatos_b(seed=4):
    rng = np.random.default_rng(seed)
    c = lienzo(1000, 600)
    puntos(c, (120, 120), 4, 7, 36, 8, rng, [NEGRO, NEGRO, CELESTE, CORAL])
    gesto(c, [(430, 450), (500, 380), (470, 500), (590, 440)], 12, rng)
    guardar(c, 'garabatos-b.webp', margen=30)


def garabatos_c(seed=9):
    rng = np.random.default_rng(seed)
    c = lienzo(1100, 500)
    gesto(c, [(80, 260), (160, 160), (140, 340), (270, 250), (380, 170), (460, 300), (580, 220)], 13, rng)
    guardar(c, 'garabatos-c.webp', margen=30)


def _ruido(w, h, sx, sy, rng):
    """Ruido suave, estirado: sx/sy son el tamaño de la mancha en píxeles."""
    base = rng.random((max(2, int(h / sy) + 2), max(2, int(w / sx) + 2)))
    img = Image.fromarray((base * 255).astype('uint8')).resize((w, h), Image.BICUBIC)
    n = np.array(img, dtype=float) / 255
    return (n - n.min()) / (n.max() - n.min() + 1e-9)


def manchon(nombre='celeste.webp', seed=5, W=2000, H=640):
    """Manchón de pintura celeste estilo graffiti: masa irregular, rocío de gotas y chorreaduras."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    campo = np.zeros((H, W))
    cx = np.linspace(260, W - 260, 18)
    for i, x in enumerate(cx):
        y = H * 0.5 + 40 * math.sin(i * 0.55) + rng.normal(0, 14)
        sx, sy = rng.uniform(110, 190), rng.uniform(60, 105)
        campo += np.exp(-(((xx - x) / sx) ** 2 + ((yy - y) / sy) ** 2))
    campo = np.clip(campo, 0, 1.4)
    rayas = _ruido(W, H, 260, 3, rng)      # cerdas: rayas finas y largas
    rayas2 = _ruido(W, H, 140, 5, rng)
    medio = _ruido(W, H, 90, 40, rng)
    fino = _ruido(W, H, 22, 14, rng)
    grueso = _ruido(W, H, 300, 160, rng)
    mod = np.clip(campo * 1.4, 0, 1)   # el ruido solo actúa donde hay pintura
    f = campo * 0.95 + mod * ((rayas - 0.5) * 0.5 + (medio - 0.5) * 0.34 + (fino - 0.5) * 0.34 + (grueso - 0.5) * 0.24)
    nucleo = np.clip((f - 0.4) / 0.035, 0, 1)
    seco = 0.55 + 0.45 * np.clip((rayas2 - 0.3) * 2.6, 0, 1)   # pintura que se corta, deja ver el papel
    alfa = nucleo * seco

    celeste = np.array(CELESTE, dtype=float)
    tono = 0.82 + 0.3 * medio + 0.3 * (rayas - 0.5)
    rgb = np.clip(celeste[None, None, :] * tono[..., None], 0, 255)
    capa = np.zeros((H, W, 4), dtype='uint8')
    capa[..., :3] = rgb.astype('uint8')
    capa[..., 3] = (alfa * 255).astype('uint8')
    img = Image.fromarray(capa, 'RGBA')

    # rocío: gotas pequeñas cerca de la masa
    cerca = np.array(Image.fromarray((nucleo * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(70)), dtype=float) / 255
    d = ImageDraw.Draw(img)
    puestas = 0
    while puestas < 2300:
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        p = cerca[int(y), int(x)] ** 1.8 * (1 - nucleo[int(y), int(x)])
        if rng.random() < p * 1.8:
            r = rng.exponential(1.3) + 0.6
            d.ellipse([x - r, y - r, x + r, y + r], fill=(*CELESTE, int(rng.uniform(150, 255))))
            puestas += 1
    # gotas grandes
    for _ in range(26):
        x, y = rng.uniform(150, W - 150), rng.uniform(40, H - 40)
        if 0.02 < cerca[int(y), int(x)] < 0.6:
            r = rng.uniform(4, 11)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(*CELESTE, 235))
    # chorreaduras desde el borde inferior
    for x in rng.uniform(380, W - 380, 7):
        col = nucleo[:, int(x)]
        ys = np.where(col > 0.6)[0]
        if len(ys) == 0:
            continue
        y0 = ys.max() - 4
        largo = rng.integers(50, 150)
        ancho = rng.uniform(5, 9)
        xs = x + np.cumsum(rng.normal(0, 0.35, largo))
        for k in range(largo):
            r = ancho / 2 * (1 - 0.25 * k / largo)
            d.ellipse([xs[k] - r, y0 + k - r, xs[k] + r, y0 + k + r], fill=(*CELESTE, 240))
        r = ancho * 0.85
        d.ellipse([xs[-1] - r, y0 + largo - r, xs[-1] + r, y0 + largo + r], fill=(*CELESTE, 240))
    guardar(img, nombre, margen=50)


if __name__ == '__main__':
    hero()
    diagonal()
    garabatos_a()
    garabatos_b()
    garabatos_c()
    manchon()
