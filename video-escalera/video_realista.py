#!/usr/bin/env python3
"""
Video vertical (1080x1920, TikTok) "Seguridad en escaleras" — estilo realista UNIPROTEC.

Entradas (ya en el repositorio):
  fotos/*.jpg              fotografías reales (licencias en fotos/creditos.json)
  fotos/logo_uniprotec.jpg logotipo original
  audio/narracion.mp3      narración ElevenLabs
  audio/alineacion.json    tiempos por carácter de la narración (ElevenLabs with-timestamps)

Salida:
  salida/escalera_uniprotec_tiktok.mp4

Uso:
  python3 video_realista.py            # render completo
  python3 video_realista.py --preview  # solo fotogramas de muestra en salida/preview_*.jpg
"""
import json
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
FOTOS = os.path.join(AQUI, "fotos")
SALIDA = os.path.join(AQUI, "salida")
FD = "/usr/share/fonts/opentype/inter"

W, H, FPS = 1080, 1920, 30
SS = 2  # supersampling de gráficos

# Colores institucionales
AZUL = (0, 134, 255)
AZUL_OSC = (11, 42, 91)
NARANJA = (255, 164, 0)
BLANCO = (255, 255, 255)
VERDE = (34, 197, 94)
ROJO = (239, 68, 68)

_fc = {}


def F(name, size):
    k = (name, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(os.path.join(FD, name), int(size * SS))
    return _fc[k]


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def appear(t, t0, d=0.35):
    return ease((t - t0) / d)


def A(c, a):
    return (*c[:3], int(255 * max(0.0, min(1.0, a))))


# ------------------------------------------------------------------ narración
ALIN = json.load(open(os.path.join(AQUI, "audio", "alineacion.json")))
TXT = "".join(ALIN["characters"])
DUR_AUDIO = ALIN["end"][-1]
COLA = 1.2
TOTAL = DUR_AUDIO + COLA


def t_de(frase, desde=0):
    i = TXT.find(frase, desde)
    assert i >= 0, frase
    return ALIN["start"][i]


def palabras():
    out, i = [], 0
    for tok in TXT.split(" "):
        j = TXT.find(tok, i)
        out.append((tok, ALIN["start"][j], ALIN["end"][j + len(tok) - 1]))
        i = j + len(tok)
    return out


PALABRAS = palabras()

T = {k: t_de(k) for k in ["Revisemos", "Uno:", "Aplica", "por cada", "Dos:", "Para acceder",
                          "sobresalir", "Tres:", "Sube", "sujétate", "no cargues", "Eleva",
                          "La prevención", "UNIPROTEC"]}

# ------------------------------------------------------------------ tomas
# win0/win1: (cx, cy, alto) de la ventana 9:16 en coordenadas de la foto (inicio → fin)
TOMAS = [
    dict(img="foto20.jpg", t0=0.0, t1=T["Revisemos"] - 0.1, win0=(512, 384, 768), win1=(512, 360, 640)),
    dict(img="foto93.jpg", t0=T["Revisemos"] - 0.1, t1=T["Uno:"] - 0.15, win0=(330, 512, 1024), win1=(360, 560, 880)),
    dict(img="foto94.jpg", t0=T["Uno:"] - 0.15, t1=T["Dos:"] - 0.15, win0=(560, 340, 680), win1=(575, 420, 520)),
    dict(img="foto74.jpg", t0=T["Dos:"] - 0.15, t1=T["Tres:"] - 0.15, win0=(520, 420, 768), win1=(560, 380, 600)),
    dict(img="foto12.jpg", t0=T["Tres:"] - 0.15, t1=T["Eleva"] - 0.15, win0=(330, 340, 683), win1=(330, 300, 560)),
    dict(img="foto4.jpg", t0=T["Eleva"] - 0.15, t1=T["La prevención"] - 0.15, win0=(330, 340, 680), win1=(720, 330, 680)),
    dict(img="foto38.jpg", t0=T["La prevención"] - 0.15, t1=T["UNIPROTEC"] - 0.25, win0=(800, 360, 683), win1=(840, 300, 540)),
]
XF = 0.35  # duración del fundido entre tomas

_img = {}


def foto(nombre):
    if nombre not in _img:
        im = Image.open(os.path.join(FOTOS, nombre)).convert("RGB")
        _img[nombre] = im
    return _img[nombre]


def ventana(toma, t):
    k = ease((t - toma["t0"]) / max(0.01, toma["t1"] - toma["t0"] + XF))
    cx = toma["win0"][0] + (toma["win1"][0] - toma["win0"][0]) * k
    cy = toma["win0"][1] + (toma["win1"][1] - toma["win0"][1]) * k
    h = toma["win0"][2] + (toma["win1"][2] - toma["win0"][2]) * k
    w = h * 9 / 16
    im = foto(toma["img"])
    # mantener dentro de la imagen
    if h > im.height:
        h = im.height
        w = h * 9 / 16
    cx = min(max(cx, w / 2), im.width - w / 2)
    cy = min(max(cy, h / 2), im.height - h / 2)
    return cx - w / 2, cy - h / 2, w, h


def frame_foto(toma, t):
    x, y, w, h = ventana(toma, t)
    im = foto(toma["img"]).resize((W, H), Image.BICUBIC, box=(x, y, x + w, y + h))
    return im, (x, y, w, h)


def a_pantalla(win, px, py):
    x, y, w, h = win
    return (px - x) / w * W, (py - y) / h * H


# ------------------------------------------------------------------ gráficos
class G:
    def __init__(self):
        self.im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def rect(self, x0, y0, x1, y1, fill=None, r=0, outline=None, w=0):
        self.d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=r * SS, fill=fill,
                                 outline=outline, width=int(w * SS))

    def line(self, pts, fill, w):
        self.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=int(w * SS), joint="curve")

    def circle(self, cx, cy, r, fill=None, outline=None, w=0):
        self.d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=fill,
                       outline=outline, width=int(w * SS))

    def arc(self, cx, cy, r, a0, a1, fill, w):
        self.d.arc([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], a0, a1, fill=fill,
                   width=int(w * SS))

    def poly(self, pts, fill):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)

    def text(self, x, y, s, f, fill, anchor="la"):
        self.d.text((x * SS, y * SS), s, font=f, fill=fill, anchor=anchor)

    def tl(self, s, f):
        return self.d.textlength(s, font=f) / SS

    def out(self):
        return self.im.resize((W, H), Image.LANCZOS)


def flecha(g, p0, p1, col, a, w=8):
    g.line([p0, p1], A(col, a), w)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    L = 26
    g.poly([p1, (p1[0] - L * math.cos(ang - 0.45), p1[1] - L * math.sin(ang - 0.45)),
            (p1[0] - L * math.cos(ang + 0.45), p1[1] - L * math.sin(ang + 0.45))], A(col, a))


def icono(g, x, y, ok, a, r=24):
    g.circle(x, y, r, fill=A(VERDE if ok else ROJO, a))
    if ok:
        g.line([(x - r * .45, y + 1), (x - r * .1, y + r * .35), (x + r * .48, y - r * .35)], A(BLANCO, a), r * .22)
    else:
        k = r * .38
        g.line([(x - k, y - k), (x + k, y + k)], A(BLANCO, a), r * .22)
        g.line([(x - k, y + k), (x + k, y - k)], A(BLANCO, a), r * .22)


def tarjeta(g, a, etiqueta, titulo, sub=None, ref=None, y=250, slide=0.0):
    """Ficha técnica: panel azul oscuro con barra naranja."""
    if a <= 0:
        return y
    x0, x1 = 64, 1016
    dx = -40 * (1 - a) + slide
    fe, ft, fs, fr = F("Inter-Bold.otf", 30), F("InterDisplay-Black.otf", 96), F("Inter-SemiBold.otf", 38), F("Inter-Medium.otf", 27)
    hgt = 70 + 110 + (60 if sub else 0) + (58 if ref else 0) + 20
    g.rect(x0 + dx, y, x1 + dx, y + hgt, fill=A(AZUL_OSC, 0.88 * a), r=22)
    g.rect(x0 + dx, y, x0 + 14 + dx, y + hgt, fill=A(NARANJA, a), r=6)
    g.text(x0 + 46 + dx, y + 30, etiqueta.upper(), fe, A(AZUL, a) if False else A((120, 190, 255), a))
    g.text(x0 + 42 + dx, y + 70, titulo, ft, A(BLANCO, a))
    yy = y + 70 + 112
    if sub:
        g.text(x0 + 46 + dx, yy, sub, fs, A(NARANJA, a))
        yy += 60
    if ref:
        g.rect(x0 + 46 + dx, yy, x0 + 46 + g.tl(ref, fr) + 36 + dx, yy + 44, fill=A(AZUL, a), r=10)
        g.text(x0 + 64 + dx, yy + 8, ref, fr, A(BLANCO, a))
    return y + hgt


def marca(g, logo_small):
    pass  # el logotipo pequeño se pega directamente sobre el fotograma (ver componer)


# ------------------------------------------------------------------ subtítulos
def grupos_subtitulos():
    """Agrupa palabras en bloques de ~3-4 palabras / máx. 24 caracteres."""
    gr, cur = [], []
    for w in PALABRAS:
        if w[0] in ("UNIPROTEC.",):
            break
        cand = " ".join(x[0] for x in cur + [w])
        if cur and (len(cand) > 24 or cur[-1][0].endswith((".", ":", "?", ","))):
            gr.append(cur)
            cur = []
        cur.append(w)
    if cur:
        gr.append(cur)
    return gr


GRUPOS = grupos_subtitulos()


def subtitulo(g, t):
    f = F("InterDisplay-ExtraBold.otf", 66)
    for i, gr in enumerate(GRUPOS):
        t0 = gr[0][1] - 0.05
        t1 = GRUPOS[i + 1][0][1] - 0.05 if i + 1 < len(GRUPOS) else gr[-1][2] + 0.3
        if t0 <= t < t1:
            words = [w[0] for w in gr]
            total = g.tl(" ".join(words), f)
            x = W / 2 - total / 2
            y = 1395
            # sombra suave
            g.rect(x - 28, y - 18, x + total + 28, y + 92, fill=(0, 0, 0, 110), r=18)
            for (wd, ws, we) in gr:
                col = NARANJA if ws <= t < we + 0.08 else BLANCO
                g.text(x, y, wd, f, A(col, 1))
                x += g.tl(wd + " ", f)
            return


# ------------------------------------------------------------------ anotaciones por toma
def overlay(g, t, toma_idx, win):
    P = lambda px, py: a_pantalla(win, px, py)

    if toma_idx == 0:  # pregunta inicial
        a = appear(t, 0.3)
        f = F("InterDisplay-Black.otf", 84)
        g.rect(64, 250, 1016, 520, fill=A(AZUL_OSC, 0.82 * a), r=24)
        g.rect(64, 250, 78, 520, fill=A(NARANJA, a), r=6)
        g.text(110, 285, "¿Esta escalera", f, A(BLANCO, a))
        g.text(110, 385, "es segura?", f, A(NARANJA, a))

    elif toma_idx == 1:  # tres puntos
        tarjeta(g, appear(t, T["Revisemos"]), "Inspección previa", "3 puntos clave", y=250)
        items = ["1  Inclinación", "2  Extensión", "3  Uso seguro"]
        f = F("Inter-Bold.otf", 46)
        for i, s in enumerate(items):
            a = appear(t, T["Revisemos"] + 0.4 + i * 0.3)
            g.rect(64, 530 + i * 92, 560, 604 + i * 92, fill=A(AZUL, 0.9 * a), r=16)
            g.text(96, 545 + i * 92, s, f, A(BLANCO, a))

    elif toma_idx == 2:  # inclinación 4:1
        # resaltar la escalera y su base
        a = appear(t, T["Aplica"] - 0.3, 0.6)
        b, tp = P(475, 680), P(662, 218)
        k = a
        g.line([b, (b[0] + (tp[0] - b[0]) * k, b[1] + (tp[1] - b[1]) * k)], A(NARANJA, 0.95), 10)
        tarjeta(g, appear(t, T["Uno:"]), "1 · Inclinación", "Regla 4 : 1",
                "Base a ¼ de la longitud · ≈ 75°", "OSHA 29 CFR 1926.1053(b)(5)(i)", y=230)
        # diagrama esquemático
        a3 = appear(t, T["por cada"] + 0.3)
        if a3 > 0:
            x0, y0 = 690, 1300
            g.rect(x0 - 40, y0 - 400, x0 + 330, y0 + 60, fill=A(AZUL_OSC, 0.85 * a3), r=18)
            base = (x0 + 30, y0)
            top = (x0 + 30 + 95, y0 - 370 + 30)
            g.line([(x0 + 125, y0 - 345), (x0 + 125, y0)], A(BLANCO, 0.6 * a3), 4)
            g.line([(x0 + 10, y0), (x0 + 300, y0)], A(BLANCO, 0.6 * a3), 4)
            g.line([base, top], A(NARANJA, a3), 10)
            fl = F("Inter-ExtraBold.otf", 40)
            g.text(x0 + 30, y0 - 210, "4 m", fl, A(BLANCO, a3), anchor="rm")
            g.text(x0 + 77, y0 + 30, "1 m", F("Inter-ExtraBold.otf", 32), A(NARANJA, a3), anchor="mm")
            g.text(x0 + 245, y0 - 360, "≈75°", F("Inter-Bold.otf", 34), A(BLANCO, a3), anchor="mm")

    elif toma_idx == 3:  # extensión 90 cm
        a = appear(t, T["Para acceder"])
        lvl_y = 415
        p0, p1 = P(300, lvl_y), P(1000, lvl_y)
        x = p0[0]
        while x < p1[0]:
            g.line([(x, p0[1]), (min(x + 34, p1[0]), p0[1])], A(BLANCO, 0.9 * a), 6)
            x += 56
        if a > 0:
            g.rect(70, p0[1] + 16, 440, p0[1] + 72, fill=A(AZUL_OSC, 0.85 * a), r=12)
            g.text(90, p0[1] + 24, "Nivel de acceso", F("Inter-Bold.otf", 34), A(BLANCO, a))
        a2 = appear(t, T["sobresalir"], 0.6)
        if a2 > 0:
            top = P(560, 305)
            bx = top[0] + 120
            ybot, ytop = p0[1], p0[1] + (top[1] - p0[1]) * a2
            g.line([(bx, ybot), (bx, ytop)], A(NARANJA, 1), 8)
            g.line([(bx - 24, ybot), (bx + 24, ybot)], A(NARANJA, 1), 8)
            if a2 >= 1:
                g.line([(bx - 24, top[1]), (bx + 24, top[1])], A(NARANJA, 1), 8)
                g.rect(bx + 30, (ybot + top[1]) / 2 - 40, bx + 260, (ybot + top[1]) / 2 + 40, fill=A(NARANJA, 1), r=14)
                g.text(bx + 145, (ybot + top[1]) / 2, "≥ 90 cm", F("InterDisplay-Black.otf", 46), A(AZUL_OSC, 1), anchor="mm")
        tarjeta(g, appear(t, T["Dos:"]), "2 · Extensión", "≥ 90 cm",
                "sobre el nivel de acceso (3 ft)", "OSHA 29 CFR 1926.1053(b)(1)", y=230)

    elif toma_idx == 4:  # uso seguro
        a = appear(t, T["Tres:"])
        tarjeta(g, a, "3 · Uso seguro", "Al subir y bajar", None, "OSHA 29 CFR 1926.1053(b)(20)–(22)", y=230)
        items = [("De frente a la escalera", True, T["Sube"]),
                 ("Al menos una mano sujeta", True, T["sujétate"]),
                 ("Sin cargar objetos", False, T["no cargues"])]
        f = F("Inter-Bold.otf", 42)
        for i, (s, ok, t0) in enumerate(items):
            ai = appear(t, t0)
            if ai <= 0:
                continue
            y = 560 + i * 92
            g.rect(64, y, 640, y + 76, fill=A(AZUL_OSC, 0.85 * ai), r=16)
            icono(g, 110, y + 38, ok, ai)
            g.text(150, y + 15, s, f, A(BLANCO, ai))

    elif toma_idx == 5:  # herramientas con cuerda
        a = appear(t, T["Eleva"])
        tarjeta(g, a, "Recomendación", "Manos libres",
                "Herramientas: elévalas con cuerda", "OSHA 29 CFR 1926.1053(b)(22)", y=230)
        a2 = appear(t, T["Eleva"] + 0.8)
        if a2 > 0:
            c = P(700, 380)
            g.circle(c[0], c[1], 130, outline=A(NARANJA, a2), w=8)

    elif toma_idx == 6:  # prevención
        a = appear(t, T["La prevención"])
        f1, f2 = F("InterDisplay-Black.otf", 80), F("InterDisplay-Black.otf", 92)
        g.rect(64, 250, 1016, 560, fill=A(AZUL_OSC, 0.85 * a), r=24)
        g.rect(64, 250, 78, 560, fill=A(NARANJA, a), r=6)
        g.text(110, 285, "La prevención", f1, A(BLANCO, a))
        g.text(110, 375, "comienza con la", f1, A(BLANCO, a))
        g.text(110, 460, "capacitación", f2, A(NARANJA, appear(t, T["La prevención"] + 0.8)))


# ------------------------------------------------------------------ logotipo
def preparar_logo():
    logo = Image.open(os.path.join(FOTOS, "logo_uniprotec.jpg")).convert("RGB")
    # fondo vertical que continúa el degradado del logotipo
    # fondo: el propio degradado del logotipo, ampliado y desenfocado
    bg = logo.resize((H, H), Image.LANCZOS).crop(((H - W) // 2, 0, (H - W) // 2 + W, H))
    bg = bg.filter(ImageFilter.GaussianBlur(120))
    # logotipo (recorte del original) con bordes difuminados
    box = (60, 270, 760, 540)
    crop = logo.crop(box)
    k = 1000 / crop.width
    crop = crop.resize((1000, int(crop.height * k)), Image.LANCZOS)
    m = Image.new("L", crop.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([40, 30, crop.width - 40, crop.height - 30], radius=90, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(40))
    bg.paste(crop, ((W - crop.width) // 2, (H - crop.height) // 2), m)
    # versión pequeña para la esquina (recorte del logotipo)
    small = logo.crop((90, 290, 740, 520)).resize((260, 92), Image.LANCZOS)
    return bg, small


LOGO_FONDO, LOGO_PEQ = preparar_logo()


def logo_frame(t_local):
    a = ease(t_local / 0.6)
    s = 1.04 - 0.04 * a
    im = LOGO_FONDO.resize((int(W * s), int(H * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


# ------------------------------------------------------------------ composición
VIG = None


def viñeta():
    global VIG
    if VIG is None:
        g = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(g)
        for i in range(H):  # oscurecer zona superior e inferior para legibilidad
            v = 0
            if i < 700:
                v = int(120 * (1 - i / 700))
            if i > 1250:
                v = int(170 * ((i - 1250) / (H - 1250)))
            d.line([(0, i), (W, i)], fill=v)
        VIG = g
    return VIG


def componer(t):
    # toma actual (y la anterior durante el fundido)
    base = None
    for idx, tm in enumerate(TOMAS):
        if tm["t0"] <= t < tm["t1"] + XF:
            im, win = frame_foto(tm, t)
            im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
            im = Image.composite(Image.new("RGB", (W, H), AZUL_OSC), im, viñeta())
            g = G()
            overlay(g, t, idx, win)
            im = Image.alpha_composite(im.convert("RGBA"), g.out()).convert("RGB")
            if base is None:
                base = im
            else:  # fundido de la toma anterior a esta
                k = ease((t - tm["t0"]) / XF)
                base = Image.blend(base, im, k)
    logo_t0 = TOMAS[-1]["t1"]
    if t >= logo_t0:
        lf = logo_frame(t - logo_t0)
        k = ease((t - logo_t0) / XF)
        base = lf if base is None else Image.blend(base, lf, k)
        return base
    # elementos fijos: logotipo pequeño, crédito, subtítulos
    base = base.convert("RGBA")
    base.alpha_composite(LOGO_PEQ.convert("RGBA"), (64, 96))
    g = G()
    subtitulo(g, t)
    base = Image.alpha_composite(base, g.out())
    return base.convert("RGB")


def render(salida):
    os.makedirs(SALIDA, exist_ok=True)
    n = int(round(TOTAL * FPS))
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", os.path.join(AQUI, "audio", "narracion.mp3"),
        "-af", f"apad=whole_dur={TOTAL},afade=t=in:d=0.05",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL}", "-movflags", "+faststart", salida,
    ], stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(componer(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"  {i}/{n}", flush=True)
    ff.stdin.close()
    if ff.wait() != 0:
        sys.exit("ffmpeg falló")
    print("Listo:", salida, f"({TOTAL:.1f} s)")


if __name__ == "__main__":
    if "--preview" in sys.argv:
        os.makedirs(SALIDA, exist_ok=True)
        ts = [1.5, 4.2, 12.5, 21.5, 28.6, 31.6, 34.2, 38.0]
        for t in ts:
            componer(t).save(os.path.join(SALIDA, f"preview_{t:05.1f}.jpg"), quality=88)
        print("ok")
    else:
        render(os.path.join(SALIDA, "escalera_uniprotec_tiktok.mp4"))
