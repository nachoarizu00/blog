"""Genera src/data/saludo.json: el saludo con la MISMA letra manuscrita del sitio (Reenie Beanie),
más los trazos de pluma (el "esqueleto" de cada letra, en orden de escritura) para animarlo.

Uso: python3 tools/escribir.py     (requiere: pip install fonttools pillow numpy)
"""
import json, math, os, tempfile
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(AQUI, '..', 'node_modules', '@fontsource', 'reenie-beanie', 'files', 'reenie-beanie-latin-400-normal.woff')
TEXTO = 'bueno, se ve que estás en'
DURACION_ESCRITURA_MS = 2600
PAUSA_LETRA_MS = 25
PAUSA_PALABRA_MS = 140
PX = 0.6            # píxeles por unidad de fuente al calcular el esqueleto
PAD = 40


def zhang_suen(B):
    B = B.astype(np.uint8)
    while True:
        cambio = False
        for paso in (0, 1):
            P = B
            n = np.roll(P, 1, 0); s = np.roll(P, -1, 0); e = np.roll(P, -1, 1); w = np.roll(P, 1, 1)
            ne = np.roll(n, -1, 1); se = np.roll(s, -1, 1); sw = np.roll(s, 1, 1); nw = np.roll(n, 1, 1)
            vec = [n, ne, e, se, s, sw, w, nw]
            suma = sum(v.astype(int) for v in vec)
            trans = sum(((vec[i] == 0) & (vec[(i + 1) % 8] == 1)).astype(int) for i in range(8))
            if paso == 0:
                c = (n * e * s == 0) & (e * s * w == 0)
            else:
                c = (n * e * w == 0) & (n * s * w == 0)
            borrar = (P == 1) & (suma >= 2) & (suma <= 6) & (trans == 1) & c
            if borrar.any():
                B[borrar] = 0
                cambio = True
        if not cambio:
            return B.astype(bool)


VEC8 = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


def vecinos(S, y, x):
    h, w = S.shape
    return [(y + dy, x + dx) for dy, dx in VEC8 if 0 <= y + dy < h and 0 <= x + dx < w and S[y + dy, x + dx]]


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = np.array(pts[0]), np.array(pts[-1])
    ab = b - a
    nrm = np.hypot(*ab)
    d = [np.hypot(*(np.array(p) - a)) if nrm == 0 else abs(ab[0] * (p[1] - a[1]) - ab[1] * (p[0] - a[0])) / nrm for p in pts]
    i = int(np.argmax(d))
    if d[i] > eps:
        return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [pts[0], pts[-1]]


def trazos_de_esqueleto(S, ancho_px):
    """Esqueleto booleano -> lista de trazos (listas de (y, x)) en orden de escritura."""
    grado = {}
    ys, xs = np.nonzero(S)
    for y, x in zip(ys, xs):
        grado[(y, x)] = len(vecinos(S, y, x))
    nodos = {p for p, g in grado.items() if g != 2}
    # agrupar nodos vecinos (cúmulos de bifurcación) en uno solo
    cluster = {}
    cid = 0
    for p in nodos:
        if p in cluster:
            continue
        pila = [p]; cluster[p] = cid
        while pila:
            q = pila.pop()
            for r in vecinos(S, *q):
                if r in nodos and r not in cluster:
                    cluster[r] = cid; pila.append(r)
        cid += 1
    cent = {}
    for p, c in cluster.items():
        cent.setdefault(c, []).append(p)
    cent = {c: (int(np.mean([q[0] for q in ps])), int(np.mean([q[1] for q in ps]))) for c, ps in cent.items()}

    aristas = []     # (nodo_a, nodo_b, [puntos])
    visto = set()
    for p in nodos:
        for r in vecinos(S, *p):
            if r in nodos or (p, r) in visto:
                continue
            cam = [cent[cluster[p]], r]
            ant, act = p, r
            visto.add((p, r))
            while act not in nodos:
                sig = [q for q in vecinos(S, *act) if q != ant and q not in nodos or (q in nodos and q != ant)]
                sig = [q for q in sig if q != ant]
                if not sig:
                    break
                prox = sig[0]
                visto.add((act, prox)); ant, act = act, prox
                cam.append(act)
            fin = cent[cluster[act]] if act in nodos else act
            cam[-1] = fin
            visto.add((act, ant))
            aristas.append((cluster[p], cluster.get(act, -1), cam))
    # evitar aristas duplicadas (recorridas en ambos sentidos)
    unicas, firmas = [], set()
    for a, b, cam in aristas:
        f = (min(cam[0], cam[-1]), max(cam[0], cam[-1]), len(cam))
        if f in firmas:
            continue
        firmas.add(f); unicas.append((a, b, cam))
    aristas = unicas

    # ciclos sin nodos (una "o" perfecta)
    en_aristas = {q for _, _, cam in aristas for q in cam}
    restantes = [p for p in grado if p not in en_aristas and p not in nodos]
    ciclos = []
    mark = set()
    for p in sorted(restantes):
        if p in mark:
            continue
        cam = [p]; mark.add(p); ant, act = None, p
        while True:
            sig = [q for q in vecinos(S, *act) if q not in mark]
            if not sig:
                break
            act = sig[0]; mark.add(act); cam.append(act)
        ciclos.append(cam)

    umbral_espiga = ancho_px * 0.9
    strokes = []
    libres = list(range(len(aristas)))

    def puntaje(p):
        return p[1] + 0.6 * p[0]

    def largo(cam):
        return sum(math.dist(cam[i], cam[i - 1]) for i in range(1, len(cam)))

    while libres:
        # nodo de arranque: extremo libre (grado 1) lo más a la izquierda/arriba posible
        cand = []
        for i in libres:
            a, b, cam = aristas[i]
            for nod, pt in ((a, cam[0]), (b, cam[-1])):
                if nod == -1:
                    cand.append((puntaje(pt) - (0 if largo(cam) > umbral_espiga else 1e6) * -1, i, nod, pt))
        if not cand:
            i = libres[0]; a, b, cam = aristas[i]; cand = [(0, i, a, cam[0])]
        cand.sort(key=lambda t: t[0])
        _, i0, nod0, pt0 = cand[0]
        a, b, cam = aristas[i0]
        actual = cam if (cam[0] == pt0) else cam[::-1]
        nodo_act = b if cam[0] == pt0 else a
        trazo = list(actual)
        libres.remove(i0)
        while True:
            sal = [i for i in libres if nodo_act != -1 and (aristas[i][0] == nodo_act or aristas[i][1] == nodo_act)]
            if not sal:
                break
            # seguir con la menor curvatura
            dir_prev = np.array(trazo[-1]) - np.array(trazo[max(0, len(trazo) - 6)])
            mejor, mejor_c = None, -9
            for i in sal:
                aa, bb, cm = aristas[i]
                ori = cm if aristas[i][0] == nodo_act else cm[::-1]
                d = np.array(ori[min(5, len(ori) - 1)]) - np.array(ori[0])
                cos = float(np.dot(dir_prev, d) / (np.linalg.norm(dir_prev) * np.linalg.norm(d) + 1e-9))
                if cos > mejor_c:
                    mejor, mejor_c, mori = i, cos, (ori, bb if aristas[i][0] == nodo_act else aa)
            ori, nodo_sig = mori
            trazo += ori[1:]
            nodo_act = nodo_sig
            libres.remove(mejor)
        strokes.append(trazo)
    for cam in ciclos:
        if len(cam) > 8:
            strokes.append(cam + [cam[0]])
    # sacar las espigas diminutas
    return [s for s in strokes if largo(s) > umbral_espiga * 0.8]


def main():
    f = TTFont(FUENTE)
    f.flavor = None
    tmp = os.path.join(tempfile.gettempdir(), 'reenie.ttf')
    f.save(tmp)
    cmap, hmtx, gs = f.getBestCmap(), f['hmtx'], f.getGlyphSet()
    fuente_pil = ImageFont.truetype(tmp, size=int(1000 * PX))
    base = int(900 * PX) + PAD

    x = 0
    contornos, trazos, bb = [], [], [1e9, 1e9, -1e9, -1e9]
    for i, ch in enumerate(TEXTO):
        nombre = cmap.get(ord(ch))
        adv = hmtx[nombre][0] if nombre else 300
        if nombre and ch != ' ':
            pen = SVGPathPen(gs)
            gs[nombre].draw(TransformPen(pen, (1, 0, 0, -1, x, 0)))
            d = pen.getCommands()
            if d:
                contornos.append(d)
            bp = BoundsPen(gs); gs[nombre].draw(TransformPen(bp, (1, 0, 0, -1, x, 0)))
            if bp.bounds:
                bb = [min(bb[0], bp.bounds[0]), min(bb[1], bp.bounds[1]), max(bb[2], bp.bounds[2]), max(bb[3], bp.bounds[3])]
            # raster del glifo
            W = int(adv * PX) + PAD * 2 + 60
            H = int(1500 * PX) + PAD
            img = Image.new('L', (W, H), 0)
            ImageDraw.Draw(img).text((PAD, base), ch, font=fuente_pil, fill=255, anchor='ls')
            B = np.array(img) > 110
            B = np.pad(B, 2)
            S = zhang_suen(B)
            area, longitud = B.sum(), max(1, S.sum())
            ancho_px = area / longitud
            tr = trazos_de_esqueleto(S, ancho_px)
            # el acento (componente aparte, arriba) se escribe al final
            def cy(t): return np.mean([p[0] for p in t])
            if len(tr) > 1:
                alto_med = np.median([cy(t) for t in tr])
                tr.sort(key=lambda t: (cy(t) < alto_med - 80 * PX * 3, ))
            for t in tr:
                pts = rdp([(p[0], p[1]) for p in t], 2.2)
                pts_u = [(round((px - 2 - PAD) / PX + x, 1), round((py - 2 - base) / PX, 1)) for py, px in pts]
                trazos.append({'glifo': i, 'pts': pts_u, 'ancho_px': float(ancho_px)})
        x += adv

    # tiempos
    def largo(pts): return sum(math.dist(pts[k], pts[k - 1]) for k in range(1, len(pts)))
    total = sum(largo(t['pts']) for t in trazos)
    vel = total / DURACION_ESCRITURA_MS
    t0, salida = 0, []
    for k, t in enumerate(trazos):
        dur = max(25, round(largo(t['pts']) / vel))
        salida.append({'d': 'M' + ' L'.join(f'{a} {b}' for a, b in t['pts']), 'inicio': round(t0), 'dur': dur})
        sig = trazos[k + 1]['glifo'] if k + 1 < len(trazos) else None
        pausa = 0                                   # dentro de una misma letra, sin levantar la pluma
        if sig is not None and sig != t['glifo']:
            j = t['glifo'] + 1
            while j < len(TEXTO) and TEXTO[j] == ',':
                j += 1
            pausa = PAUSA_PALABRA_MS if (j >= len(TEXTO) or TEXTO[j] == ' ') else PAUSA_LETRA_MS
        t0 += dur + pausa
    grosor = round(float(np.median([t['ancho_px'] for t in trazos])) / PX * 2.1)
    margen = 80
    datos = {
        'texto': TEXTO,
        'viewBox': f'{round(bb[0]) - margen} {round(bb[1]) - margen} {round(bb[2] - bb[0]) + margen * 2} {round(bb[3] - bb[1]) + margen * 2}',
        'contorno': ' '.join(contornos),
        'grosor': grosor,
        'duracion': round(t0),
        'trazos': salida,
    }
    destino = os.path.join(AQUI, '..', 'src', 'data', 'saludo.json')
    with open(destino, 'w') as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=1)
    print(f'{len(salida)} trazos, grosor {grosor}, {t0 / 1000:.1f} s, viewBox {datos["viewBox"]}')


if __name__ == '__main__':
    main()
