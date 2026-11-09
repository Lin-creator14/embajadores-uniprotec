#!/usr/bin/env python3
"""
Genera el video vertical (1080x1920, TikTok) "Seguridad en escaleras" de UNIPROTEC.

- Narración: ElevenLabs (text-to-speech) si hay una API key válida.
  Si no, genera un borrador sin voz con duraciones estimadas.
- Imagen: ilustraciones y diagramas dibujados por código (Pillow).
- Montaje: ffmpeg.

Uso:
    python3 generar_video.py                 # intenta ElevenLabs; si falla, borrador sin voz
    python3 generar_video.py --sin-voz       # fuerza el borrador sin voz
    python3 generar_video.py --voz VOICE_ID  # usa una voz concreta de ElevenLabs

Variables de entorno opcionales:
    ELEVENLABS_API_KEY   clave (si no la inyecta el proxy del entorno)
    ELEVENLABS_VOICE_ID  voz a usar
    ELEVENLABS_MODEL     modelo (por defecto eleven_multilingual_v2)
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 30
SS = 2  # supersampling para bordes suaves

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "salida")
FONT_DIR = "/usr/share/fonts/opentype/inter"

# ---------------------------------------------------------------- colores
NAVY_TOP = (14, 42, 71)
NAVY_BOT = (8, 24, 42)
BUILDING = (36, 72, 110)
BUILDING_EDGE = (58, 102, 144)
GROUND = (52, 60, 72)
YELLOW = (242, 183, 5)
ORANGE = (255, 122, 26)
SKIN = (224, 168, 130)
PANTS = (31, 42, 54)
BOX = (176, 122, 66)
WHITE = (255, 255, 255)
MUTED = (170, 190, 210)
GREEN = (46, 204, 113)
RED = (231, 76, 60)


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(size * SS))


# ---------------------------------------------------------------- guion
# narr: texto que lee la voz; cap: subtítulo (None = sin subtítulo, la escena ya muestra el texto)
ESCENAS = [
    dict(id="intro", narr="Observa esta situación. ¿Esta escalera está colocada de manera segura?",
         cap="Observa esta situación. ¿Esta escalera está colocada de manera segura?"),
    dict(id="tres", narr="A simple vista puede parecer correcta, pero hay tres puntos que debemos analizar.",
         cap="A simple vista puede parecer correcta, pero hay 3 puntos que debemos analizar."),
    dict(id="t1", narr="Primero: la inclinación.", cap=None),
    dict(id="regla", narr="OSHA establece la regla de cuatro a uno para escaleras portátiles apoyadas sobre una estructura.",
         cap="OSHA establece la regla 4 a 1 para escaleras portátiles apoyadas sobre una estructura."),
    dict(id="metros", narr="Esto significa que por cada cuatro metros de longitud de trabajo de la escalera, la base debe separarse aproximadamente un metro de la pared.",
         cap="Por cada 4 m de longitud de trabajo de la escalera, la base se separa aprox. 1 m de la pared."),
    dict(id="t2", narr="Segundo: la altura de acceso.", cap=None),
    dict(id="altura", narr="Cuando se utiliza una escalera para subir a un techo o plataforma, sus largueros deben sobresalir al menos noventa centímetros por encima del nivel de acceso.",
         cap="Para subir a un techo o plataforma, los largueros deben sobresalir al menos 90 cm por encima del nivel de acceso."),
    dict(id="t3", narr="Tercero: observa al trabajador. Está subiendo con una caja en la mano, lo que puede comprometer su equilibrio.",
         cap="Tercero: observa al trabajador. Sube con una caja en la mano, lo que puede comprometer su equilibrio."),
    dict(id="mano", narr="OSHA establece que, al subir o bajar, el trabajador debe sujetarse con al menos una mano y no debe transportar objetos que puedan provocar una pérdida del equilibrio.",
         cap="Al subir o bajar: sujétate con al menos una mano y no cargues objetos que te hagan perder el equilibrio."),
    dict(id="cuerda", narr="Las herramientas y materiales pueden elevarse utilizando una cuerda.",
         cap="Las herramientas y materiales pueden elevarse con una cuerda."),
    dict(id="recuerda", narr="Recuerda: una escalera no solo debe estar bien colocada; también debe utilizarse correctamente.",
         cap="Recuerda: una escalera no solo debe estar bien colocada; también debe usarse correctamente."),
    dict(id="prevencion", narr="La prevención comienza con la capacitación.", cap=None),
    dict(id="marca", narr="UNIPROTEC. Innovando en capacitación.", cap=None),
]


# ---------------------------------------------------------------- ElevenLabs
API = "https://api.elevenlabs.io/v1"


def _req(path, data=None, accept="application/json"):
    key = os.environ.get("ELEVENLABS_API_KEY", "sk_proxy-injected")  # el proxy del entorno sustituye la clave
    headers = {"xi-api-key": key, "Accept": accept}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def elegir_voz():
    if os.environ.get("ELEVENLABS_VOICE_ID"):
        return os.environ["ELEVENLABS_VOICE_ID"]
    voces = json.loads(_req("/voices"))["voices"]
    # preferir una voz con acento latino/español
    for v in voces:
        labels = json.dumps(v.get("labels", {})).lower()
        if any(k in labels for k in ("latin", "mexic", "spanish", "español", "colombian", "argentin")):
            print(f"Voz elegida: {v['name']} ({v['voice_id']})")
            return v["voice_id"]
    v = voces[0]
    print(f"Voz elegida (primera disponible): {v['name']} ({v['voice_id']})")
    return v["voice_id"]


def tts(texto, voz, destino):
    modelo = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
    audio = _req(f"/text-to-speech/{voz}?output_format=mp3_44100_128",
                 data={"text": texto, "model_id": modelo,
                       "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.2}},
                 accept="audio/mpeg")
    with open(destino, "wb") as f:
        f.write(audio)


def duracion(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", path])
    return float(out)


# ---------------------------------------------------------------- dibujo
class D:
    """Envoltura de ImageDraw que trabaja en coordenadas 1x."""

    def __init__(self, img):
        self.img = img
        self.d = ImageDraw.Draw(img, "RGBA")
        self.k = 1.0  # zoom de la ilustración
        self.c = (0, 0)

    def zoom(self, k=1.12, c=(600, 1300)):
        self.k, self.c = k, c

    def unzoom(self):
        self.k, self.c = 1.0, (0, 0)

    def P(self, x, y):
        return ((x - self.c[0]) * self.k + self.c[0]) * SS, ((y - self.c[1]) * self.k + self.c[1]) * SS

    def line(self, pts, fill, w):
        self.d.line([self.P(x, y) for x, y in pts], fill=fill, width=int(w * SS * self.k), joint="curve")
        for x, y in (pts[0], pts[-1]):
            r = w / 2
            self.circle(x, y, r, fill=fill)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, w=0, r=0):
        self.d.rounded_rectangle([*self.P(x0, y0), *self.P(x1, y1)], radius=r * SS * self.k,
                                 fill=fill, outline=outline, width=int(w * SS * self.k))

    def circle(self, cx, cy, r, fill=None, outline=None, w=0):
        self.d.ellipse([*self.P(cx - r, cy - r), *self.P(cx + r, cy + r)],
                       fill=fill, outline=outline, width=int(w * SS * self.k))

    def poly(self, pts, fill):
        self.d.polygon([self.P(x, y) for x, y in pts], fill=fill)

    def arc(self, cx, cy, r, a0, a1, fill, w):
        self.d.arc([*self.P(cx - r, cy - r), *self.P(cx + r, cy + r)], a0, a1,
                   fill=fill, width=int(w * SS * self.k))

    def text(self, x, y, txt, f, fill, anchor="mm", stroke=0, stroke_fill=(0, 0, 0)):
        self.d.text(self.P(x, y), txt, font=f, fill=fill, anchor=anchor,
                    stroke_width=int(stroke * SS), stroke_fill=stroke_fill)

    def textlen(self, txt, f):
        return self.d.textlength(txt, font=f) / SS


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def prog(t, start, length=0.5):
    return ease((t - start) / length)


def alpha(c, a):
    return (*c[:3], int(255 * max(0, min(1, a))))


# geometría de la escena
GROUND_Y = 1250
WALL_X = 640
ROOF_Y = 610
PX_M = 150  # píxeles por metro


def ladder_geom(kind):
    """Devuelve base, apoyo, punta, vector unitario y longitud de trabajo."""
    h = GROUND_Y - ROOF_Y
    if kind == "right":   # 4:1 y 90 cm por encima
        L = h / math.sqrt(1 - 1 / 16)
        off = L / 4
        ext = 0.9 * PX_M
    else:                 # muy vertical y sin sobresalir
        off = 85
        ext = 0
        L = math.hypot(h, off)
    B = (WALL_X - off, GROUND_Y)
    S = (WALL_X, ROOF_Y)
    u = ((S[0] - B[0]) / L, (S[1] - B[1]) / L)
    T = (S[0] + u[0] * ext, S[1] + u[1] * ext)
    return dict(B=B, S=S, T=T, u=u, L=L, ext=ext, off=off)


def along(g, dist):
    return (g["B"][0] + g["u"][0] * dist, g["B"][1] + g["u"][1] * dist)


def draw_background(d):
    d.zoom()
    # edificio y suelo
    d.rect(WALL_X, ROOF_Y, 1180, GROUND_Y, fill=BUILDING)
    d.rect(WALL_X - 6, ROOF_Y - 14, 1180, ROOF_Y + 4, fill=BUILDING_EDGE)
    for i, yy in enumerate(range(ROOF_Y + 60, GROUND_Y, 70)):  # líneas de bloque
        d.line([(WALL_X, yy), (1080, yy)], fill=(255, 255, 255, 18), w=3)
    d.rect(800, 900, 960, 1250, fill=(26, 54, 84))  # puerta
    d.rect(-200, GROUND_Y, 1280, GROUND_Y + 14, fill=(80, 92, 108))
    d.rect(-200, GROUND_Y + 14, 1280, 1340, fill=GROUND)


def draw_ladder(d, g, a=1.0):
    ux, uy = g["u"]
    nx, ny = -uy, ux  # perpendicular
    half = 17
    top_len = g["L"] + g["ext"]
    for sgn in (-1, 1):
        p0 = (g["B"][0] + nx * half * sgn, g["B"][1] + ny * half * sgn)
        p1 = (p0[0] + ux * top_len, p0[1] + uy * top_len)
        d.line([p0, p1], fill=alpha(YELLOW, a), w=11)
    dist = 40
    while dist < top_len - 10:
        c = along(g, dist)
        d.line([(c[0] - nx * half, c[1] - ny * half), (c[0] + nx * half, c[1] + ny * half)],
               fill=alpha((214, 160, 0), a), w=7)
        dist += 52
    # zapatas
    d.rect(g["B"][0] - 30, GROUND_Y - 8, g["B"][0] + 30, GROUND_Y + 4, fill=alpha((40, 40, 40), a), r=4)


def draw_worker(d, g, s, mode="box", a=1.0, foot=None, flip=False):
    """Trabajador sobre la escalera. s = distancia (px) del pie desde la base.
    mode: 'box' (caja en una mano) o 'hands' (ambas manos en la escalera)."""
    P = along(g, s) if foot is None else foot
    hip = (P[0] - 34, P[1] - 100)
    sh = (hip[0] + 12, hip[1] - 92)
    head = (sh[0] + 6, sh[1] - 42)
    c = lambda col: alpha(col, a)
    # piernas
    foot2 = along(g, s + 60) if foot is None else (P[0] + 10, P[1])
    knee1 = (hip[0] - 4, hip[1] + 55)
    knee2 = (hip[0] + 30, hip[1] + 30)
    d.line([hip, knee1, P], fill=c(PANTS), w=24)
    d.line([hip, knee2, foot2], fill=c(PANTS), w=24)
    d.rect(P[0] - 6, P[1] - 10, P[0] + 26, P[1] + 4, fill=c((20, 20, 20)), r=4)
    d.rect(foot2[0] - 6, foot2[1] - 10, foot2[0] + 26, foot2[1] + 4, fill=c((20, 20, 20)), r=4)
    # brazo trasero
    if foot is None:
        hand1 = along(g, s + 230)
    else:
        hand1 = (sh[0] + 60, sh[1] + 40)
    d.line([sh, ((sh[0] + hand1[0]) / 2 + 6, (sh[1] + hand1[1]) / 2 + 18), hand1], fill=c(ORANGE), w=20)
    d.circle(*hand1, 11, fill=c(SKIN))
    # torso (chaleco)
    d.line([hip, sh], fill=c(ORANGE), w=56)
    d.line([(hip[0] - 4, hip[1] - 30), (sh[0] - 4, sh[1] + 30)], fill=c((230, 230, 230)), w=6)  # reflectivo
    # cabeza y casco
    d.circle(*head, 26, fill=c(SKIN))
    d.d.pieslice([*d.P(head[0] - 31, head[1] - 34), *d.P(head[0] + 31, head[1] + 24)],
                 180, 360, fill=c(YELLOW))
    d.rect(head[0] - 36, head[1] - 7, head[0] + 38, head[1] - 1, fill=c(YELLOW), r=3)
    # brazo delantero
    box_pos = None
    if mode == "box":
        hand2 = (sh[0] - 58, sh[1] + 70)
        d.line([sh, (sh[0] - 40, sh[1] + 40), hand2], fill=c(ORANGE), w=20)
        box_pos = (hand2[0] - 12, hand2[1] + 10)
        bx, by = box_pos
        d.rect(bx - 48, by - 40, bx + 32, by + 26, fill=c(BOX), r=6)
        d.line([(bx - 48, by - 14), (bx + 32, by - 14)], fill=c((140, 92, 48)), w=4)
        d.circle(*hand2, 11, fill=c(SKIN))
    else:
        hand2 = along(g, s + 180) if foot is None else (sh[0] - 40, sh[1] - 50)
        d.line([sh, ((sh[0] + hand2[0]) / 2 - 6, (sh[1] + hand2[1]) / 2 + 22), hand2], fill=c(ORANGE), w=20)
        d.circle(*hand2, 11, fill=c(SKIN))
    return dict(head=head, sh=sh, hip=hip, box=box_pos, hand=hand2)


def badge(d, x, y, n, a=1.0, col=YELLOW, size=1.0):
    r = 34 * size
    d.circle(x, y, r + 5, fill=alpha((0, 0, 0), 0.35 * a))
    d.circle(x, y, r, fill=alpha(col, a))
    d.text(x, y + 2, str(n), font("Inter-Black.otf", 40 * size), alpha(NAVY_BOT, a))


def check(d, x, y, a=1.0, ok=True, r=40):
    col = GREEN if ok else RED
    d.circle(x, y, r, fill=alpha(col, a))
    if ok:
        d.line([(x - r * 0.45, y + 2), (x - r * 0.1, y + r * 0.35), (x + r * 0.5, y - r * 0.35)],
               fill=alpha(WHITE, a), w=r * 0.2)
    else:
        k = r * 0.38
        d.line([(x - k, y - k), (x + k, y + k)], fill=alpha(WHITE, a), w=r * 0.2)
        d.line([(x - k, y + k), (x + k, y - k)], fill=alpha(WHITE, a), w=r * 0.2)


def dim_line(d, p0, p1, label, t_prog, side=1, col=YELLOW, f=None, offset=0, a=1.0):
    """Cota que crece de p0 a p1 con etiqueta."""
    if t_prog <= 0:
        return
    f = f or font("Inter-ExtraBold.otf", 44)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln * side, dx / ln * side
    a0 = (p0[0] + nx * offset, p0[1] + ny * offset)
    a1 = (a0[0] + dx * t_prog, a0[1] + dy * t_prog)
    d.line([a0, a1], fill=alpha(col, a), w=6)
    for p in (a0, (a0[0] + dx, a0[1] + dy)):
        if p is a0 or t_prog >= 1:
            d.line([(p[0] - nx * 16, p[1] - ny * 16), (p[0] + nx * 16, p[1] + ny * 16)], fill=alpha(col, a), w=6)
    if t_prog >= 0.6:
        la = (t_prog - 0.6) / 0.4
        mx, my = a0[0] + dx / 2 + nx * 48, a0[1] + dy / 2 + ny * 48
        tw = d.textlen(label, f)
        d.rect(mx - tw / 2 - 18, my - 34, mx + tw / 2 + 18, my + 34, fill=alpha(col, la), r=14)
        d.text(mx, my + 2, label, f, alpha(NAVY_BOT, la))


def header(d, label=None, a=1.0):
    d.unzoom()
    d.text(60, 130, "UNIPROTEC", font("InterDisplay-Black.otf", 40), alpha(YELLOW, a), anchor="lm")
    if label:
        f = font("Inter-Bold.otf", 30)
        tw = d.textlen(label, f)
        d.rect(1020 - tw - 40, 102, 1020, 158, fill=alpha((255, 255, 255), 0.12 * a), r=28)
        d.text(1020 - tw / 2 - 20, 131, label, f, alpha(WHITE, a))


def headline(d, small, big, a=1.0, size=120):
    d.unzoom()
    d.text(70, 235, small, font("Inter-Bold.otf", 42), alpha(MUTED, a), anchor="lm")
    d.text(64, 315, big, font("InterDisplay-Black.otf", size), alpha(YELLOW, a), anchor="lm")


def checklist(d, items, t, y0=245, step=80, size=42):
    d.unzoom()
    for i, (txt, ok, st) in enumerate(items):
        a = prog(t, st)
        if a > 0:
            y = y0 + i * step
            check(d, 96, y, a, ok, r=30)
            d.text(146, y, txt, font("Inter-Bold.otf", size), alpha(WHITE, a), anchor="lm")


def big_title(d, lines, y, size=92, col=WHITE, a=1.0, fname="InterDisplay-Black.otf", gap=1.12):
    f = font(fname, size)
    for i, ln in enumerate(lines):
        d.text(W / 2, y + i * size * gap, ln, f, alpha(col, a))


# ---------------------------------------------------------------- escenas
def sc_intro(d, t, dur):
    g = ladder_geom("wrong")
    draw_background(d)
    draw_ladder(d, g)
    draw_worker(d, g, 260 - 20 * min(1, t / dur), "box")
    a = prog(t, 0.8)
    if a > 0:
        f = font("InterDisplay-Black.otf", 230)
        d.text(330, 520 - 20 * (1 - a), "?", f, alpha(YELLOW, a), stroke=6, stroke_fill=alpha(NAVY_BOT, a))
    header(d, "SEGURIDAD EN ESCALERAS")


def sc_tres(d, t, dur):
    g = ladder_geom("wrong")
    draw_background(d)
    draw_ladder(d, g)
    w = draw_worker(d, g, 240, "box")
    pts = [(g["B"][0] - 80, GROUND_Y - 60), (g["S"][0] - 70, g["S"][1] - 30), (w["box"][0] - 80, w["box"][1] - 40)]
    for i, (x, y) in enumerate(pts):
        a = prog(t, 0.6 + i * 0.7, 0.35)
        if a > 0:
            badge(d, x, y, i + 1, a, size=0.8 + 0.2 * a)
    header(d, "3 PUNTOS CLAVE")


def sc_title(n, word):
    def f(d, t, dur):
        a = prog(t, 0, 0.4)
        y_off = 40 * (1 - a)
        d.circle(W / 2, 760 + y_off, 170, fill=alpha(YELLOW, a))
        d.text(W / 2, 770 + y_off, str(n), font("InterDisplay-Black.otf", 220), alpha(NAVY_BOT, a))
        a2 = prog(t, 0.25, 0.4)
        big_title(d, [word], 1060 + 30 * (1 - a2), size=96, a=a2)
        d.rect(W / 2 - 80, 1160, W / 2 + 80 * (2 * a2 - 1), 1170, fill=alpha(YELLOW, a2), r=5)
        header(d, f"PUNTO {n} DE 3")
    return f


def sc_regla(d, t, dur):
    g = ladder_geom("right")
    draw_background(d)
    draw_ladder(d, g)
    # cotas: a lo largo de la escalera y en la base
    dim_line(d, g["B"], g["S"], "4", prog(t, 0.6, 0.9), side=1, offset=70)
    dim_line(d, (g["B"][0], GROUND_Y + 40), (WALL_X, GROUND_Y + 40), "1", prog(t, 1.6, 0.6), side=1, offset=0)
    # ángulo
    a = prog(t, 2.3)
    if a > 0:
        ang = math.degrees(math.atan2(GROUND_Y - ROOF_Y, g["off"]))
        d.arc(g["B"][0], GROUND_Y, 110, -ang, 0, alpha(WHITE, a), 5)
        d.text(g["B"][0] + 170, GROUND_Y - 50, f"≈{ang:.0f}°", font("Inter-Bold.otf", 36), alpha(WHITE, a))
    a = prog(t, 0.2)
    headline(d, "Regla", "4 : 1", a, 130)
    header(d, "1 · INCLINACIÓN")


def sc_metros(d, t, dur):
    g = ladder_geom("right")
    draw_background(d)
    draw_ladder(d, g)
    dim_line(d, g["B"], g["S"], "4 m", 1.0, side=1, offset=70)
    dim_line(d, (g["B"][0], GROUND_Y + 40), (WALL_X, GROUND_Y + 40), "1 m", prog(t, 0.3, 0.6), side=1)
    a = prog(t, dur * 0.55)
    if a > 0:
        check(d, 120, 1150, a, True, r=46)
    headline(d, "Longitud de trabajo", "4 m → 1 m", 1.0, 110)
    header(d, "1 · INCLINACIÓN")


def sc_altura(d, t, dur):
    g = ladder_geom("right")
    draw_background(d)
    # línea del nivel de acceso
    a = prog(t, 0.3)
    xx = 0
    while xx < 1080:
        d.line([(xx, ROOF_Y), (min(xx + 30, 1080), ROOF_Y)], fill=alpha(WHITE, 0.7 * a), w=4)
        xx += 50
    draw_ladder(d, g)
    d.text(985, ROOF_Y - 40, "Nivel de acceso", font("Inter-Bold.otf", 32), alpha(WHITE, a), anchor="rm")
    # cota vertical de la extensión
    top_y = g["T"][1]
    x = g["T"][0] + 105
    dim_line(d, (x, ROOF_Y), (x, top_y), "90 cm", prog(t, 1.0, 0.8), side=-1, offset=0,
             f=font("Inter-ExtraBold.otf", 40))
    a = prog(t, 2.0)
    if a > 0:
        headline(d, "Al menos", "90 cm", a, 130)
    header(d, "2 · ALTURA DE ACCESO")


def sc_t3(d, t, dur):
    g = ladder_geom("wrong")
    draw_background(d)
    draw_ladder(d, g)
    w = draw_worker(d, g, 250, "box")
    a = prog(t, 0.2, 0.4)
    if a > 0:
        d.unzoom()
        d.text(W / 2, 250, "3", font("InterDisplay-Black.otf", 110), alpha(YELLOW, a))
        d.text(W / 2, 345, "EL TRABAJADOR", font("InterDisplay-Black.otf", 68), alpha(WHITE, a))
        d.zoom()
    a = prog(t, dur * 0.45, 0.4)
    if a > 0:
        bx, by = w["box"]
        d.circle(bx - 8, by - 7, 85 + 20 * (1 - a), outline=alpha(RED, a), w=9)
        check(d, bx - 100, by - 80, a, ok=False, r=34)
    header(d, "PUNTO 3 DE 3")


def sc_mano(d, t, dur):
    g = ladder_geom("right")
    draw_background(d)
    draw_ladder(d, g)
    w = draw_worker(d, g, 200 + 40 * min(1, t / dur), "hands")
    a = prog(t, 0.4)
    hx, hy = w["hand"]
    if a > 0:
        d.circle(hx, hy, 46 + 10 * (1 - a), outline=alpha(GREEN, a), w=8)
    checklist(d, [("Sujétate con al menos una mano", True, 0.6),
                  ("Sin objetos que te desequilibren", False, dur * 0.5)], t)
    header(d, "3 · USO CORRECTO")


def sc_cuerda(d, t, dur):
    g = ladder_geom("right")
    draw_background(d)
    draw_ladder(d, g)
    # trabajador en el techo jalando la cuerda
    foot = (900, ROOF_Y - 14)
    w = draw_worker(d, g, 0, "hands", foot=foot)
    rope_x = 690
    k = ease(t / max(dur * 0.85, 0.1))
    load_y = GROUND_Y - 60 - (GROUND_Y - 60 - (ROOF_Y + 80)) * k
    # polea / borde
    d.line([w["hand"], (rope_x, ROOF_Y - 20)], fill=(220, 200, 160), w=5)
    d.line([(rope_x, ROOF_Y - 20), (rope_x, load_y - 40)], fill=(220, 200, 160), w=5)
    # cubeta con herramientas
    d.poly([(rope_x - 45, load_y - 40), (rope_x + 45, load_y - 40), (rope_x + 35, load_y + 40),
            (rope_x - 35, load_y + 40)], fill=(90, 110, 130))
    d.line([(rope_x - 20, load_y - 40), (rope_x - 35, load_y - 85)], fill=(200, 200, 210), w=10)
    d.line([(rope_x + 15, load_y - 40), (rope_x + 25, load_y - 80)], fill=(220, 60, 40), w=12)
    a = prog(t, 0.3)
    headline(d, "Materiales", "con cuerda", a, 110)
    header(d, "3 · USO CORRECTO")


def sc_recuerda(d, t, dur):
    g = ladder_geom("right")
    draw_background(d)
    draw_ladder(d, g)
    draw_worker(d, g, 230, "hands")
    checklist(d, [("Inclinación 4 : 1", True, 0.4), ("90 cm sobre el acceso", True, 1.0),
                  ("Una mano siempre", True, 1.6)], t, y0=230, step=72, size=40)
    header(d, "RECUERDA")


def sc_prevencion(d, t, dur):
    a = prog(t, 0, 0.5)
    big_title(d, ["La prevención", "comienza con la"], 760 - 30 * (1 - a), size=96, a=a)
    a2 = prog(t, 0.6, 0.5)
    big_title(d, ["capacitación."], 760 + 2 * 96 * 1.12, size=118, col=YELLOW, a=a2)
    header(d)


def sc_marca(d, t, dur):
    a = prog(t, 0, 0.6)
    s = 0.9 + 0.1 * a
    d.rect(W / 2 - 300 * s, 760, W / 2 + 300 * s, 768, fill=alpha(YELLOW, a), r=4)
    d.text(W / 2, 880, "UNIPROTEC", font("InterDisplay-Black.otf", 150 * s), alpha(WHITE, a))
    a2 = prog(t, 0.7, 0.6)
    d.text(W / 2, 1010 + 20 * (1 - a2), "Innovando en capacitación", font("Inter-SemiBold.otf", 54),
           alpha(YELLOW, a2))
    d.rect(W / 2 - 300 * s, 1090, W / 2 + 300 * s, 1098, fill=alpha(YELLOW, a), r=4)


DIBUJO = {
    "intro": sc_intro, "tres": sc_tres, "t1": sc_title(1, "INCLINACIÓN"), "regla": sc_regla,
    "metros": sc_metros, "t2": sc_title(2, "ALTURA DE ACCESO"), "altura": sc_altura, "t3": sc_t3,
    "mano": sc_mano, "cuerda": sc_cuerda, "recuerda": sc_recuerda, "prevencion": sc_prevencion,
    "marca": sc_marca,
}


# ---------------------------------------------------------------- subtítulos
CAP_FONT = None


def wrap(text, f, maxw, d):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        cand = (cur + " " + wd).strip()
        if d.textlen(cand, f) <= maxw:
            cur = cand
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def caption_chunks(text, d):
    f = font("Inter-ExtraBold.otf", 58)
    lines = wrap(text, f, 900, d)
    chunks = [lines[i:i + 2] for i in range(0, len(lines), 2)]
    total = sum(len(" ".join(c)) for c in chunks)
    out, acc = [], 0.0
    for c in chunks:
        n = len(" ".join(c))
        out.append((acc / total, (acc + n) / total, c))
        acc += n
    return out


def draw_caption(d, chunks, frac):
    d.unzoom()
    f = font("Inter-ExtraBold.otf", 58)
    for a0, a1, lines in chunks:
        if a0 <= frac < a1 or (a1 == 1.0 and frac >= 1.0):
            lh = 76
            y0 = 1480 - (len(lines) - 1) * lh / 2
            maxw = max(d.textlen(ln, f) for ln in lines)
            d.rect(W / 2 - maxw / 2 - 30, y0 - 52, W / 2 + maxw / 2 + 30, y0 + (len(lines) - 1) * lh + 52,
                   fill=(0, 0, 0, 150), r=24)
            for i, ln in enumerate(lines):
                d.text(W / 2, y0 + i * lh, ln, f, WHITE, stroke=2, stroke_fill=(0, 0, 0))
            return


# ---------------------------------------------------------------- render
def make_bg():
    bg = Image.new("RGB", (W * SS, H * SS))
    px = ImageDraw.Draw(bg)
    for y in range(H * SS):
        k = y / (H * SS)
        col = tuple(int(NAVY_TOP[i] + (NAVY_BOT[i] - NAVY_TOP[i]) * k) for i in range(3))
        px.line([(0, y), (W * SS, y)], fill=col)
    return bg


def render(escenas, duraciones, wav_path, out_path):
    bg = make_bg()
    total = sum(duraciones)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path,
    ], stdin=subprocess.PIPE)
    n_total = int(round(total * FPS))
    t_start = 0.0
    frame = 0
    for esc, dur in zip(escenas, duraciones):
        n = int(round((t_start + dur) * FPS)) - frame
        tmp = Image.new("RGB", (10, 10))
        chunks = caption_chunks(esc["cap"], D(tmp)) if esc["cap"] else None
        for i in range(n):
            t = i / FPS
            img = bg.copy()
            d = D(img)
            DIBUJO[esc["id"]](d, t, dur)
            if chunks:
                # el subtítulo avanza con la voz (ligeramente adelantado)
                draw_caption(d, chunks, min(1.0, t / max(dur - 0.5, 0.1)))
            # fundido corto entre escenas
            fade = min(1.0, t / 0.18, (dur - t) / 0.18) if esc["id"] != "marca" else min(1.0, t / 0.18)
            out = img.reduce(SS)
            if fade < 1.0:
                out = Image.blend(Image.new("RGB", out.size, NAVY_BOT), out, max(0.0, fade))
            ff.stdin.write(out.tobytes())
            frame += 1
        t_start += dur
        print(f"  escena {esc['id']:<11} {dur:5.2f}s  ({frame}/{n_total} cuadros)", flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg falló")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-voz", action="store_true")
    ap.add_argument("--voz", help="voice_id de ElevenLabs")
    ap.add_argument("--solo", help="renderizar solo estas escenas (ids separados por coma)")
    args = ap.parse_args()
    if args.voz:
        os.environ["ELEVENLABS_VOICE_ID"] = args.voz

    os.makedirs(SALIDA, exist_ok=True)
    work = tempfile.mkdtemp(prefix="video_escalera_")
    escenas = ESCENAS
    if args.solo:
        ids = args.solo.split(",")
        escenas = [e for e in ESCENAS if e["id"] in ids]

    con_voz = False
    if not args.sin_voz:
        try:
            voz = elegir_voz()
            con_voz = True
        except urllib.error.HTTPError as e:
            print(f"ElevenLabs no disponible ({e.code}: {e.read()[:200]!r}). Se genera un borrador sin voz.")
        except Exception as e:  # noqa: BLE001
            print(f"ElevenLabs no disponible ({e}). Se genera un borrador sin voz.")

    PAUSA = 0.45
    partes, duraciones = [], []
    for i, esc in enumerate(escenas):
        wav = os.path.join(work, f"{i:02d}.wav")
        if con_voz:
            mp3 = os.path.join(work, f"{i:02d}.mp3")
            print(f"Voz: {esc['id']}")
            tts(esc["narr"], voz, mp3)
            dur = duracion(mp3) + PAUSA
            subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-af",
                                   f"apad=whole_dur={dur}", "-ar", "44100", "-ac", "2", wav])
        else:
            palabras = len(esc["narr"].split())
            dur = palabras / 2.6 + 0.9
            subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                                   "anullsrc=r=44100:cl=stereo", "-t", f"{dur}", wav])
        if esc["id"] == "marca":
            dur += 1.0
            subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af",
                                   f"apad=whole_dur={dur}", wav + ".pad.wav"])
            os.replace(wav + ".pad.wav", wav)
        partes.append(wav)
        duraciones.append(dur)

    lista = os.path.join(work, "lista.txt")
    with open(lista, "w") as f:
        f.writelines(f"file '{p}'\n" for p in partes)
    audio = os.path.join(work, "narracion.wav")
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lista,
                           "-c", "copy", audio])
    if con_voz:
        subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-i", audio,
                               os.path.join(SALIDA, "narracion.mp3")])

    nombre = "escalera_tiktok.mp4" if con_voz else "escalera_tiktok_borrador_sin_voz.mp4"
    out = os.path.join(SALIDA, nombre)
    print(f"Renderizando {sum(duraciones):.1f}s de video…")
    render(escenas, duraciones, audio, out)
    print(f"Listo: {out}")


if __name__ == "__main__":
    main()
