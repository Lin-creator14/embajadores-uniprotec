#!/usr/bin/env python3
"""
Video promocional UNIPROTEC · Cursos: Liderazgo Proactivo · Growth Mindset · LEGO® SERIOUS PLAY®
Vertical 1080x1920, ~36 s. Tomas reales del taller (clips/), voz ElevenLabs, música propia.

  python3 promo.py            # render → salida/uniprotec_cursos_promo.mp4
  python3 promo.py --preview  # fotogramas de muestra
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(AQUI, "..", "video-escalera", "fotos", "logo_uniprotec.jpg")
FD = "/usr/share/fonts/opentype/inter"
W, H, FPS, SS = 1080, 1920, 30, 2
AZUL, AZUL_OSC, NARANJA, BLANCO = (0, 134, 255), (11, 42, 91), (255, 164, 0), (255, 255, 255)
CORREO = "ventasoficial@uniprotec.net"

_fc = {}


def F(n, s):
    if (n, s) not in _fc:
        _fc[(n, s)] = ImageFont.truetype(os.path.join(FD, n), int(s * SS))
    return _fc[(n, s)]


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def ap(t, t0, d=0.3):
    return ease((t - t0) / d)


def A(c, a):
    return (*c[:3], int(255 * max(0.0, min(1.0, a))))


# ------------------------------------------------------------------ tiempos de la voz
AL = json.load(open(os.path.join(AQUI, "audio", "alineacion.json")))
TXT = "".join(AL["characters"])


def ts(frase, desde=0):
    i = TXT.find(frase, desde)
    assert i >= 0, frase
    return AL["start"][i]


T = {k: ts(k) for k in ["siguiente", "En UNIPROTEC", "experiencia", "Liderazgo", "anticipan", "inspiran",
                        "decisiones", "Growth", "aprender", "adaptarse", "superar", "LEGO", "ideas",
                        "estrategias", "en equipo", "Lleva", "Escríbenos", "UNIPROTEC. Innovando"]}
FIN = AL["end"][-1]
LOGO_T0 = T["UNIPROTEC. Innovando"] - 0.25
TOTAL = FIN + 0.7

# ------------------------------------------------------------------ tomas: (clip, inicio en el clip, t0, t1, zoom dir)
TOMAS = [
    (5, 0.3, 0.0, 1.6, 1), (3, 3.8, 1.6, T["En UNIPROTEC"], -1),
    (6, 0.0, T["En UNIPROTEC"], 5.2, 1), (1, 4.5, 5.2, T["Liderazgo"], -1),
    (2, 0.5, T["Liderazgo"], 11.6, 1), (4, 0.5, 11.6, T["Growth"], -1),
    (5, 4.0, T["Growth"], 18.3, 1), (2, 9.6, 18.3, T["LEGO"], -1),
    (3, 0.0, T["LEGO"], 24.8, 1), (6, 2.1, 24.8, T["Lleva"], -1),
    (1, 0.3, T["Lleva"], LOGO_T0 + 0.4, 1),
]
CORTES_FLASH = {T["Liderazgo"], T["Growth"], T["LEGO"]}  # destello blanco al presentar cada curso


DIFUMINAR_ROSTROS = True
MODELO_ROSTROS = os.path.join(AQUI, "modelos", "face_detection_yunet_2023mar.onnx")  # OpenCV Zoo, Apache-2.0


UMBRAL = 0.62


def anonimizar(frames, n):
    """Detecta rostros (YuNet) y los difumina con una elipse suave, estable en el tiempo."""
    import cv2
    cache = os.path.join(AQUI, "salida", f"rostros_toma{n}.json")
    if os.path.exists(cache):
        todas = json.load(open(cache))
    else:
        det = cv2.FaceDetectorYN.create(MODELO_ROSTROS, "", (W // 2, H // 2), 0.4, 0.3, 5000)
        todas = []
        for fr in frames:
            small = cv2.resize(fr, (W // 2, H // 2))
            _, caras = det.detect(cv2.cvtColor(small, cv2.COLOR_RGB2BGR))
            todas.append([] if caras is None else [[float(v) for v in c[:4] * 2] + [float(c[-1])] for c in caras])
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump(todas, open(cache, "w"))
    # solo detecciones confiables y de tamaño de rostro razonable
    cajas = [[tuple(c[:4]) for c in f if c[4] >= UMBRAL and 0.6 < c[3] / max(c[2], 1) < 2.2 and c[2] < W * 0.4]
             for f in todas]
    out = frames.copy()
    VENT = 5  # unión de detecciones de ±5 fotogramas (evita parpadeos y huecos)
    for i in range(len(frames)):
        bs = [b for j in range(max(0, i - VENT), min(len(frames), i + VENT + 1)) for b in cajas[j]]
        if not bs:
            continue
        fr = out[i]
        blur = cv2.GaussianBlur(fr, (0, 0), 28)
        mask = np.zeros((H, W), np.float32)
        for x, y, bw, bh in bs:
            cx, cy = x + bw / 2, y + bh / 2 - bh * 0.1
            cv2.ellipse(mask, (int(cx), int(cy)), (int(bw * 0.85), int(bh * 1.0)), 0, 0, 360, 1.0, -1)
        mask = cv2.GaussianBlur(mask, (0, 0), 12)[..., None]
        out[i] = (fr * (1 - mask) + blur * mask).astype(np.uint8)
    return out


def cargar(n):
    src = os.path.join(AQUI, "clips", f"toma{n}.mov")
    vf = (f"fps={FPS},hqdn3d=1.5:1.5:3:3,scale={W}:{H}:flags=lanczos,"
          f"unsharp=5:5:0.8:3:3:0.3,eq=contrast=1.06:saturation=1.18:brightness=0.015,setsar=1")
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-an", "-vf", vf, "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    return anonimizar(frames, n) if DIFUMINAR_ROSTROS else frames


CLIPS = {}


def frame_toma(k, t):
    n, s0, t0, t1, zd = TOMAS[k]
    if n not in CLIPS:
        CLIPS[n] = cargar(n)
    fr = CLIPS[n]
    i = min(int((s0 + (t - t0)) * FPS), len(fr) - 1)
    im = Image.fromarray(fr[i])
    p = (t - t0) / max(0.1, t1 - t0)
    z = 1.04 + 0.08 * p if zd > 0 else 1.12 - 0.08 * p  # empuje / alejamiento de cámara
    w2, h2 = W / z, H / z
    dx = 20 * zd * (p - 0.5)
    return im.resize((W, H), Image.BICUBIC, box=((W - w2) / 2 + dx, (H - h2) / 2, (W + w2) / 2 + dx, (H + h2) / 2))


# ------------------------------------------------------------------ gráficos
class G:
    def __init__(self):
        self.im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def rect(self, x0, y0, x1, y1, fill=None, r=0):
        self.d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=r * SS, fill=fill)

    def circle(self, cx, cy, r, fill):
        self.d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], fill=fill)

    def text(self, x, y, s, f, fill, anchor="la"):
        self.d.text((x * SS, y * SS), s, font=f, fill=fill, anchor=anchor)

    def tl(self, s, f):
        return self.d.textlength(s, font=f) / SS

    def out(self):
        return self.im.resize((W, H), Image.LANCZOS)


def chip(g, x, y, s, a, bg=AZUL, fg=BLANCO, size=30):
    f = F("Inter-Bold.otf", size)
    w = g.tl(s, f)
    g.rect(x, y, x + w + 40, y + size + 26, fill=A(bg, a), r=(size + 26) / 2)
    g.text(x + 20, y + 12, s, f, A(fg, a))


def texto_grande(g, x, y, lineas, a, size=110, color=BLANCO, dx=0):
    f = F("InterDisplay-Black.otf", size)
    for i, (s, col) in enumerate(lineas):
        ai = ap(a, i * 0.12, 0.5) if isinstance(a, float) else a
        g.text(x - 60 * (1 - ai) + dx + 4, y + i * size * 1.02 + 5, s, f, A((0, 0, 0), 0.45 * ai))
        g.text(x - 60 * (1 - ai) + dx, y + i * size * 1.02, s, f, A(col or color, ai))


def curso(g, t, t0, num, nombre, items, tiempos):
    """Presentación de curso: chip 'CURSO 0n', título grande y 3 atributos."""
    a = ap(t, t0 - 0.05, 0.45)
    if a <= 0:
        return
    chip(g, 64, 250, f"CURSO {num:02d}", a, bg=NARANJA, fg=AZUL_OSC)
    f = F("InterDisplay-Black.otf", 108)
    y = 330
    for i, linea in enumerate(nombre):
        ai = ap(t, t0 + 0.08 * i, 0.45)
        g.text(64 - 80 * (1 - ai) + 4, y + 5, linea, f, A((0, 0, 0), 0.45 * ai))
        g.text(64 - 80 * (1 - ai), y, linea, f, A(BLANCO, ai))
        y += 112
    # barra azul bajo el título
    g.rect(64, y + 14, 64 + 300 * ap(t, t0 + 0.2, 0.5), y + 24, fill=A(AZUL, a), r=5)
    y += 60
    for s, ti in zip(items, tiempos):
        ai = ap(t, ti - 0.1, 0.3)
        if ai > 0:
            fi = F("Inter-Bold.otf", 44)
            w = g.tl(s, fi)
            g.rect(64, y, 64 + w + 92, y + 78, fill=A(AZUL_OSC, 0.88 * ai), r=18)
            g.circle(100, y + 39, 13, A(NARANJA, ai))
            g.text(128 - 30 * (1 - ai), y + 15, s, fi, A(BLANCO, ai))
            y += 94


def capa(g, t):
    if t < T["En UNIPROTEC"]:
        a = ap(t, 0.15, 0.4)
        texto_grande(g, 64, 300, [("¿TU EQUIPO", None), ("ESTÁ LISTO", None), ("PARA EL", None),
                                  ("SIGUIENTE", NARANJA), ("NIVEL?", NARANJA)], a, size=118)
    elif t < T["Liderazgo"] - 0.1:
        a = ap(t, T["En UNIPROTEC"], 0.4)
        chip(g, 64, 250, "UNIPROTEC", a)
        texto_grande(g, 64, 330, [("CAPACITACIÓN", None), ("QUE SE VIVE", NARANJA)],
                     ap(t, T["experiencia"] - 0.3, 0.4), size=104)
    elif t < T["Growth"] - 0.1:
        curso(g, t, T["Liderazgo"], 1, ["LIDERAZGO", "PROACTIVO"],
              ["Anticipación", "Inspiración", "Mejores decisiones"],
              [T["anticipan"], T["inspiran"], T["decisiones"]])
    elif t < T["LEGO"] - 0.1:
        curso(g, t, T["Growth"], 2, ["GROWTH", "MINDSET"],
              ["Aprender", "Adaptarse", "Superar retos"],
              [T["aprender"], T["adaptarse"], T["superar"]])
    elif t < T["Lleva"] - 0.1:
        curso(g, t, T["LEGO"], 3, ["LEGO®", "SERIOUS PLAY®"],
              ["Ideas", "Estrategia", "Trabajo en equipo"],
              [T["ideas"], T["estrategias"], T["en equipo"]])
    elif t < LOGO_T0:
        a = ap(t, T["Lleva"], 0.4)
        texto_grande(g, 64, 300, [("LLEVA ESTOS", None), ("CURSOS A TU", None), ("EMPRESA", NARANJA)], a, size=112)
        a2 = ap(t, T["Escríbenos"] - 0.2, 0.35)
        if a2 > 0:
            fc = F("Inter-Bold.otf", 44)
            w = g.tl(CORREO, fc)
            y = 1180
            g.rect(W / 2 - w / 2 - 40, y, W / 2 + w / 2 + 40, y + 92, fill=A(NARANJA, a2), r=46)
            g.text(W / 2, y + 46, CORREO, fc, A(AZUL_OSC, a2), anchor="mm")


# ------------------------------------------------------------------ subtítulos
CLAVE = {"equipo", "nivel", "uniprotec", "capacitación", "experiencia", "liderazgo", "proactivo", "líderes",
         "growth", "mindset", "crecimiento", "lego", "serious", "play", "ideas", "estrategias", "empresa",
         "decisiones", "reto", "manos"}


def grupos():
    pal, i = [], 0
    for tok in TXT.split(" "):
        j = TXT.find(tok, i)
        pal.append((tok, AL["start"][j], AL["end"][j + len(tok) - 1]))
        i = j + len(tok)
    gr, cur = [], []
    for w in pal:
        if w[1] >= LOGO_T0:
            break
        if cur and (len(" ".join(x[0] for x in cur + [w])) > 20 or cur[-1][0].endswith((".", ":", "?", ","))):
            gr.append(cur)
            cur = []
        cur.append(w)
    return gr + ([cur] if cur else [])


GR = grupos()


def subtitulos(g, t):
    f = F("InterDisplay-ExtraBold.otf", 58)
    for i, gr in enumerate(GR):
        t0 = gr[0][1] - 0.05
        t1 = GR[i + 1][0][1] - 0.05 if i + 1 < len(GR) else gr[-1][2] + 0.25
        if t0 <= t < t1:
            total = g.tl(" ".join(w[0] for w in gr), f)
            x, y = W / 2 - total / 2, 1500
            g.rect(x - 24, y - 14, x + total + 24, y + 80, fill=(0, 0, 0, 125), r=16)
            for wd, ws, we in gr:
                col = NARANJA if wd.strip("¿?¡!.,:").lower() in CLAVE else BLANCO
                al = 1.0 if t >= ws - 0.02 else 0.55  # las palabras se encienden al pronunciarse
                g.text(x, y, wd, f, A(col, al))
                x += g.tl(wd + " ", f)
            return


# ------------------------------------------------------------------ cierre
def preparar_logo():
    logo = Image.open(LOGO).convert("RGB")
    s = 1000 / logo.width
    lg = logo.resize((1000, int(logo.height * s)), Image.LANCZOS)
    bg = Image.new("RGB", (W, H), logo.getpixel((3, 3)))
    bg.paste(lg, ((W - lg.width) // 2, (H - lg.height) // 2 - 120))
    g = G()
    yb = (H + lg.height) // 2 - 20
    f1 = F("Inter-SemiBold.otf", 40)
    g.text(W / 2, yb, "Liderazgo Proactivo · Growth Mindset", f1, A(BLANCO, 1), anchor="mm")
    g.text(W / 2, yb + 56, "LEGO® SERIOUS PLAY®", f1, A(BLANCO, 1), anchor="mm")
    fc = F("Inter-Bold.otf", 42)
    w = g.tl(CORREO, fc)
    g.rect(W / 2 - w / 2 - 36, yb + 120, W / 2 + w / 2 + 36, yb + 200, fill=A(NARANJA, 1), r=40)
    g.text(W / 2, yb + 160, CORREO, fc, A(AZUL_OSC, 1), anchor="mm")
    return Image.alpha_composite(bg.convert("RGBA"), g.out()).convert("RGB")


def degradado():
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for y in range(H):
        v = int(150 * (1 - y / 900)) if y < 900 else (int(160 * (y - 1350) / (H - 1350)) if y > 1350 else 0)
        d.line([(0, y), (W, y)], fill=max(0, v))
    return m


def main():
    logo = preparar_logo()
    sombra = degradado()
    oscuro = Image.new("RGB", (W, H), AZUL_OSC)
    blanco = Image.new("RGB", (W, H), (255, 255, 255))

    def componer(t):
        if t >= LOGO_T0 + 0.35:
            k = ease((t - LOGO_T0 - 0.35) / 0.4)
            s = 1.06 - 0.06 * k
            im = logo.resize((int(W * s), int(H * s)), Image.LANCZOS)
            x, y = (im.width - W) // 2, (im.height - H) // 2
            return im.crop((x, y, x + W, y + H))
        k = max(i for i, tm in enumerate(TOMAS) if tm[2] <= t)
        im = frame_toma(k, t)
        im = Image.composite(oscuro, im, sombra)
        g = G()
        capa(g, t)
        subtitulos(g, t)
        im = Image.alpha_composite(im.convert("RGBA"), g.out()).convert("RGB")
        t0 = TOMAS[k][2]
        if t0 in CORTES_FLASH and t - t0 < 0.18:
            im = Image.blend(im, blanco, 0.6 * (1 - (t - t0) / 0.18))
        if t >= LOGO_T0:  # fundido al logotipo
            im = Image.blend(im, logo, ease((t - LOGO_T0) / 0.35))
        return im

    out_dir = os.path.join(AQUI, "salida")
    os.makedirs(out_dir, exist_ok=True)
    if "--preview" in sys.argv:
        for t in [1.0, 4.5, 10.8, 13.5, 17.5, 20.5, 24.0, 27.5, 31.5, 35.5]:
            componer(t).save(os.path.join(out_dir, f"preview_{t:04.1f}.jpg"), quality=88)
        print("ok")
        return
    out = os.path.join(out_dir, "uniprotec_cursos_promo.mp4")
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", os.path.join(AQUI, "audio", "narracion.mp3"), "-i", os.path.join(AQUI, "audio", "musica.mp3"),
        "-filter_complex",
        f"[1:a]adelay=50|50,apad[v];[2:a]volume=0.22[m];[v][m]amix=inputs=2:duration=longest:normalize=0,"
        f"atrim=0:{TOTAL},afade=t=out:st={TOTAL - 1.0}:d=1.0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{TOTAL}", "-movflags", "+faststart", out,
    ], stdin=subprocess.PIPE)
    n = int(round(TOTAL * FPS))
    for i in range(n):
        ff.stdin.write(componer(i / FPS).tobytes())
        if i % 200 == 0:
            print(f"  {i}/{n}", flush=True)
    ff.stdin.close()
    if ff.wait():
        sys.exit("ffmpeg falló")
    print("Listo:", out, f"({TOTAL:.1f} s)")


if __name__ == "__main__":
    main()
