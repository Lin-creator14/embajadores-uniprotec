#!/usr/bin/env python3
"""
Video UNIPROTEC · Inspección del montacargas antes de operar (Reels/TikTok 9:16, ~39,6 s).

Entradas:
  clips/escena1.mp4 … clips/escena6.mp4   clips de video (cualquier tamaño; se recortan a 9:16)
  audio/narracion.mp3 + audio/alineacion.json   voz ElevenLabs y tiempos por carácter
  audio/musica.mp3                        música de fondo (musica.py)
  ../video-escalera/fotos/logo_uniprotec.jpg   logotipo original

Salida: salida/montacargas_uniprotec.mp4

  python3 montar_video.py             # render completo
  python3 montar_video.py --preview   # fotogramas de muestra en salida/preview_*.jpg

Si falta un clip se usa un fondo provisional con el número de escena.
La posición de círculos/flechas de cada escena se ajusta en MARCAS (fracciones 0–1 de la pantalla).
"""
import glob
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "salida")
LOGO = os.path.join(AQUI, "..", "video-escalera", "fotos", "logo_uniprotec.jpg")
FD = "/usr/share/fonts/opentype/inter"
W, H, FPS, SS = 1080, 1920, 30, 2

AZUL, AZUL_OSC, NARANJA, BLANCO = (0, 134, 255), (11, 42, 91), (255, 164, 0), (255, 255, 255)
VERDE, ROJO = (34, 197, 94), (239, 68, 68)
CORREO = "ventasoficial@uniprotec.net"

_fc = {}


def F(n, s):
    if (n, s) not in _fc:
        _fc[(n, s)] = ImageFont.truetype(os.path.join(FD, n), int(s * SS))
    return _fc[(n, s)]


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ap(t, t0, d=0.35):
    return ease((t - t0) / d)


def A(c, a):
    return (*c[:3], int(255 * max(0.0, min(1.0, a))))


# ------------------------------------------------------------------ narración y tiempos
AL = json.load(open(os.path.join(AQUI, "audio", "alineacion.json")))
TXT = "".join(AL["characters"])


def ts(frase):
    i = TXT.find(frase)
    assert i >= 0, frase
    return AL["start"][i]


T = {k: ts(k) for k in ["¿Sabías", "Primero", "Verifica", "Después", "Asegúrate", "Comprueba", "frenos",
                        "dirección", "luces", "alarma", "Y muy", "no utilices", "Repórtala", "Recuerda",
                        "¡Capacita", "UNIPROTEC"]}
FIN_VOZ = AL["end"][-1]
TOTAL = FIN_VOZ + 0.6

ESCENAS = [  # (inicio, fin)
    (0.0, T["Primero"]), (T["Primero"], T["Después"]), (T["Después"], T["Comprueba"]),
    (T["Comprueba"], T["Y muy"]), (T["Y muy"], T["Recuerda"]), (T["Recuerda"], T["UNIPROTEC"] - 0.2),
]
LOGO_T0 = T["UNIPROTEC"] - 0.2
XF = 0.3

# Posiciones de marcas (fracción de pantalla) por escena; ajustar al ver los clips
MARCAS = {
    2: dict(circulo=(0.50, 0.62, 0.20)),             # llanta
    3: dict(flechas=[(0.30, 0.60), (0.70, 0.62)]),     # horquillas
    4: dict(circulo=(0.50, 0.55, 0.16)),             # controles
}


# ------------------------------------------------------------------ lectura de clips
class Clip:
    def __init__(self, n, dur_obj):
        self.frames = None
        cand = sorted(glob.glob(os.path.join(AQUI, "clips", f"escena{n}.*")))
        self.n = n
        if cand:
            src = cand[0]
            # recorte a 9:16 + escala a 1080x1920 + 30 fps
            vf = (f"scale='if(gt(a,9/16),-2,{W})':'if(gt(a,9/16),{H},-2)',"
                  f"crop={W}:{H},fps={FPS},setsar=1")
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-an", "-vf", vf,
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
            self.frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
            dur_clip = len(self.frames) / FPS
            # cámara lenta suave si el clip es más corto que la escena (máx. ×1,3)
            self.rate = max(1 / 1.3, min(1.0, dur_clip / max(dur_obj, 0.1)))
        else:
            self.rate = 1.0

    def frame(self, t_local):
        if self.frames is None:
            im = Image.new("RGB", (W, H), AZUL_OSC)
            d = ImageDraw.Draw(im)
            d.text((W / 2, H / 2), f"ESCENA {self.n}\n(clip pendiente)", font=ImageFont.truetype(
                os.path.join(FD, "Inter-Bold.otf"), 60), fill=(80, 120, 170), anchor="mm", align="center")
            return im
        i = min(int(t_local * self.rate * FPS), len(self.frames) - 1)
        return Image.fromarray(self.frames[i])


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
        self.d.arc([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], a0, a1, fill=fill, width=int(w * SS))

    def poly(self, pts, fill):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)

    def text(self, x, y, s, f, fill, anchor="la"):
        self.d.text((x * SS, y * SS), s, font=f, fill=fill, anchor=anchor)

    def tl(self, s, f):
        return self.d.textlength(s, font=f) / SS

    def out(self):
        return self.im.resize((W, H), Image.LANCZOS)


def wrap(g, s, f, maxw):
    out, cur = [], ""
    for w in s.split():
        c = (cur + " " + w).strip()
        if g.tl(c, f) <= maxw:
            cur = c
        else:
            out.append(cur)
            cur = w
    return out + [cur]


def titulo(g, a, num, texto, sub=None, ref=None, y=230):
    """Panel de título: número en círculo naranja + texto blanco sobre azul oscuro."""
    if a <= 0:
        return
    dx = -50 * (1 - a)
    ft = F("InterDisplay-Black.otf", 62)
    x0 = 64 + dx
    tx = x0 + (130 if num else 40)
    lines = wrap(g, texto, ft, 1016 - tx - 30)
    h = 40 + len(lines) * 72 + (56 if sub else 0) + (56 if ref else 0) + 24
    g.rect(x0, y, 1016 + dx, y + h, fill=A(AZUL_OSC, 0.9 * a), r=24)
    g.rect(x0, y, x0 + 12, y + h, fill=A(NARANJA, a), r=6)
    if num:
        g.circle(x0 + 72, y + 74, 40, fill=A(NARANJA, a))
        g.text(x0 + 72, y + 76, str(num), F("InterDisplay-Black.otf", 50), A(AZUL_OSC, a), anchor="mm")
    yy = y + 36
    for ln in lines:
        g.text(tx, yy, ln, ft, A(BLANCO, a))
        yy += 72
    if sub:
        g.text(tx, yy + 8, sub, F("Inter-SemiBold.otf", 36), A(NARANJA, a))
        yy += 56
    if ref:
        fr = F("Inter-Medium.otf", 26)
        g.rect(tx, yy + 10, tx + g.tl(ref, fr) + 32, yy + 52, fill=A(AZUL, a), r=10)
        g.text(tx + 16, yy + 17, ref, fr, A(BLANCO, a))


def check_item(g, x, y, s, a, ok=True):
    if a <= 0:
        return
    f = F("Inter-Bold.otf", 42)
    w = g.tl(s, f)
    g.rect(x, y, x + w + 110, y + 76, fill=A(AZUL_OSC, 0.88 * a), r=18)
    g.circle(x + 40, y + 38, 22, fill=A(VERDE if ok else ROJO, a))
    g.line([(x + 30, y + 39), (x + 37, y + 47), (x + 51, y + 30)], A(BLANCO, a), 5)
    g.text(x + 76, y + 16, s, f, A(BLANCO, a))


def circulo(g, fx, fy, fr, a, t):
    if a <= 0:
        return
    cx, cy, r = fx * W, fy * H, fr * W
    pulse = 1 + 0.03 * math.sin(t * 6)
    g.arc(cx, cy, r * pulse, -90, -90 + 360 * a, A(NARANJA, 1), 9)


def flecha(g, fx, fy, a, desde=(-1, -1)):
    if a <= 0:
        return
    x1, y1 = fx * W, fy * H
    L = 170 * a
    n = math.hypot(*desde)
    ux, uy = desde[0] / n, desde[1] / n
    x0, y0 = x1 + ux * (L + 40), y1 + uy * (L + 40)
    xe, ye = x1 + ux * 40, y1 + uy * 40
    g.line([(x0, y0), (xe, ye)], A(NARANJA, 1), 12)
    ang = math.atan2(ye - y0, xe - x0)
    k = 36
    g.poly([(xe + 10 * math.cos(ang), ye + 10 * math.sin(ang)),
            (xe - k * math.cos(ang - 0.5), ye - k * math.sin(ang - 0.5)),
            (xe - k * math.cos(ang + 0.5), ye - k * math.sin(ang + 0.5))], A(NARANJA, 1))


def advertencia(g, cx, cy, s, a):
    if a <= 0:
        return
    s *= 0.85 + 0.15 * a
    h = s * 0.87
    pts = [(cx, cy - h / 2), (cx + s / 2, cy + h / 2), (cx - s / 2, cy + h / 2)]
    g.poly(pts, A(NARANJA, a))
    g.text(cx, cy + h * 0.12, "!", F("InterDisplay-Black.otf", s * 0.55), A(AZUL_OSC, a), anchor="mm")


# ------------------------------------------------------------------ subtítulos
CLAVE = {"inspección", "previa", "accidentes", "llantas", "daños", "horquillas", "grietas", "deformaciones",
         "desgaste", "frenos", "dirección", "luces", "alarma", "reversa", "falla", "repórtala", "inmediato",
         "segura", "capacita", "equipo", "montacargas", "motor"}


def palabras():
    out, i = [], 0
    for tok in TXT.split(" "):
        j = TXT.find(tok, i)
        out.append((tok, AL["start"][j], AL["end"][j + len(tok) - 1]))
        i = j + len(tok)
    return out


def grupos():
    gr, cur = [], []
    for w in palabras():
        if w[0].startswith("UNIPROTEC"):
            break
        if cur and (len(" ".join(x[0] for x in cur + [w])) > 22 or cur[-1][0].endswith((".", ":", "?", ",", "!"))):
            gr.append(cur)
            cur = []
        cur.append(w)
    return gr + ([cur] if cur else [])


GR = grupos()


def subtitulos(g, t):
    f = F("InterDisplay-ExtraBold.otf", 64)
    for i, gr in enumerate(GR):
        t0 = gr[0][1] - 0.05
        t1 = GR[i + 1][0][1] - 0.05 if i + 1 < len(GR) else gr[-1][2] + 0.3
        if t0 <= t < t1:
            total = g.tl(" ".join(w[0] for w in gr), f)
            x, y = W / 2 - total / 2, 1420
            g.rect(x - 26, y - 16, x + total + 26, y + 90, fill=(0, 0, 0, 120), r=18)
            for wd, ws, we in gr:
                limpio = wd.strip("¿?¡!.,:").lower()
                col = NARANJA if limpio in CLAVE else BLANCO
                g.text(x, y, wd, f, A(col, 1))
                if ws <= t < we + 0.06:  # palabra que se pronuncia: subrayado azul
                    ww = g.tl(wd, f)
                    g.rect(x, y + 80, x + ww, y + 88, fill=A(AZUL, 1), r=4)
                x += g.tl(wd + " ", f)
            return


# ------------------------------------------------------------------ capas por escena
def capa(g, n, t):
    if n == 1:
        titulo(g, ap(t, 0.3), None, "¿REVISAS TU MONTACARGAS ANTES DE OPERARLO?")
        a = ap(t, T["¿Sabías"])
        if a > 0:
            titulo(g, a, None, "Inspección previa diaria",
                   "Antes de poner el equipo en servicio", "OSHA 29 CFR 1910.178(q)(7)", y=1050)
    elif n == 2:
        titulo(g, ap(t, T["Primero"]), 1, "REVISA LAS LLANTAS", "Sin cortes, grietas ni desgaste visible")
        m = MARCAS[2]["circulo"]
        circulo(g, *m, ap(t, T["Primero"] + 0.4, 0.7), t)
    elif n == 3:
        titulo(g, ap(t, T["Después"]), 2, "VERIFICA LAS HORQUILLAS",
               "Sin grietas, deformaciones ni desgaste")
        for k, (fx, fy) in enumerate(MARCAS[3]["flechas"]):
            flecha(g, fx, fy, ap(t, T["Asegúrate"] + 0.3 * k, 0.5), desde=(-1 if k == 0 else 1, -1.2))
    elif n == 4:
        titulo(g, ap(t, T["Comprueba"]), 3, "COMPRUEBA SU FUNCIONAMIENTO")
        for k, (s, key) in enumerate([("Frenos", "frenos"), ("Dirección", "dirección"), ("Luces", "luces"),
                                      ("Alarma de reversa", "alarma")]):
            check_item(g, 64, 520 + k * 96, s, ap(t, T[key] - 0.1))
        m = MARCAS[4]["circulo"]
        circulo(g, *m, ap(t, T["frenos"], 0.6), t)
    elif n == 5:
        a = ap(t, T["Y muy"])
        advertencia(g, W / 2, 330, 220, a)
        if a > 0:
            titulo(g, ap(t, T["no utilices"] - 0.3), None, "SI DETECTAS UNA FALLA, NO OPERES EL EQUIPO.",
                   "Repórtala de inmediato", "OSHA 29 CFR 1910.178(p)(1)", y=480)
    elif n == 6:
        titulo(g, ap(t, T["Recuerda"]), None, "Operar seguro comienza antes de encender el motor")
        a = ap(t, T["¡Capacita"])
        if a > 0:
            f1 = F("InterDisplay-Black.otf", 96)
            g.rect(64, 1000, 1016, 1260, fill=A(NARANJA, a), r=26)
            g.text(W / 2, 1080, "¡CAPACITA A", f1, A(AZUL_OSC, a), anchor="mm")
            g.text(W / 2, 1180, "TU EQUIPO!", f1, A(AZUL_OSC, a), anchor="mm")


# ------------------------------------------------------------------ cierre con logotipo
def preparar_logo():
    logo = Image.open(LOGO).convert("RGB")  # original, sin modificar
    s = 1000 / logo.width
    lg = logo.resize((1000, int(logo.height * s)), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), logo.getpixel((3, 3)))
    bg.paste(lg, ((W - lg.width) // 2, (H - lg.height) // 2 - 80))
    g = G()
    g.text(W / 2, (H + lg.height) // 2 + 10, "Fortalece la seguridad en cada operación",
           F("Inter-SemiBold.otf", 40), A(BLANCO, 1), anchor="mm")
    fc = F("Inter-Bold.otf", 42)
    tw = g.tl(CORREO, fc)
    yb = (H + lg.height) // 2 + 90
    g.rect(W / 2 - tw / 2 - 34, yb - 38, W / 2 + tw / 2 + 34, yb + 38, fill=A(NARANJA, 1), r=38)
    g.text(W / 2, yb, CORREO, fc, A(AZUL_OSC, 1), anchor="mm")
    return Image.alpha_composite(bg.convert("RGBA"), g.out()).convert("RGB")


# ------------------------------------------------------------------ composición
def degradado():
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for y in range(H):
        v = 0
        if y < 650:
            v = int(110 * (1 - y / 650))
        if y > 1300:
            v = int(170 * (y - 1300) / (H - 1300))
        d.line([(0, y), (W, y)], fill=v)
    return m


def main():
    preview = "--preview" in sys.argv
    clips = [Clip(i + 1, e[1] - e[0] + XF) for i, e in enumerate(ESCENAS)]
    logo = preparar_logo()
    sombra = degradado()
    oscuro = Image.new("RGB", (W, H), AZUL_OSC)

    def componer(t):
        base = None
        for i, (t0, t1) in enumerate(ESCENAS):
            if t0 <= t < t1 + XF:
                tl = t - t0
                fr = clips[i].frame(tl)
                # zoom lento (empuje de cámara) para dinamismo
                z = 1.0 + 0.06 * ease(tl / (t1 - t0 + XF))
                if z > 1.001:
                    w2, h2 = W / z, H / z
                    fr = fr.resize((W, H), Image.BICUBIC, box=((W - w2) / 2, (H - h2) / 2, (W + w2) / 2, (H + h2) / 2))
                fr = Image.composite(oscuro, fr, sombra)
                g = G()
                capa(g, i + 1, t)
                fr = Image.alpha_composite(fr.convert("RGBA"), g.out()).convert("RGB")
                base = fr if base is None else Image.blend(base, fr, ease((t - t0) / XF))
        if t >= LOGO_T0:
            k = ease((t - LOGO_T0) / 0.5)
            return logo if base is None else Image.blend(base, logo, k)
        g = G()
        subtitulos(g, t)
        return Image.alpha_composite(base.convert("RGBA"), g.out()).convert("RGB")

    os.makedirs(SALIDA, exist_ok=True)
    if preview:
        for t in [1.5, 7.0, 11.5, 17.5, 24.5, 29.5, 35.5, 38.5]:
            componer(t).save(os.path.join(SALIDA, f"preview_{t:04.1f}.jpg"), quality=88)
        print("ok")
        return

    out = os.path.join(SALIDA, "montacargas_uniprotec.mp4")
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", os.path.join(AQUI, "audio", "narracion.mp3"),
        "-i", os.path.join(AQUI, "audio", "musica.mp3"),
        "-filter_complex",
        f"[1:a]apad,atrim=0:{TOTAL}[v];[2:a]volume=0.13,atrim=0:{TOTAL},afade=t=out:st={TOTAL - 1.5}:d=1.5[m];"
        f"[v][m]amix=inputs=2:duration=first:normalize=0[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL}", "-movflags", "+faststart", out,
    ], stdin=subprocess.PIPE)
    n = int(round(TOTAL * FPS))
    for i in range(n):
        ff.stdin.write(componer(i / FPS).tobytes())
        if i % 150 == 0:
            print(f"  {i}/{n}", flush=True)
    ff.stdin.close()
    if ff.wait():
        sys.exit("ffmpeg falló")
    print("Listo:", out, f"({TOTAL:.1f} s)")


if __name__ == "__main__":
    main()
