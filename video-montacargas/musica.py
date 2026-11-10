#!/usr/bin/env python3
"""Música corporativa instrumental sintetizada (sin derechos de terceros).

Progresión I–V–vi–IV en Re mayor, 100 BPM: pad suave + arpegio pluck + pulso grave + hi-hat ligero.
Genera audio/musica.wav (~41 s) con fundidos de entrada y salida.
"""
import os
import sys
import wave

import numpy as np

SR = 44100
BPM = 100
BEAT = 60 / BPM
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 41.0
AQUI = os.path.dirname(os.path.abspath(__file__))

N = int(SR * DUR)
t_all = np.arange(N) / SR


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


# acordes (MIDI) — D, A, Bm, G ; cada acorde dura 2 compases (8 tiempos)
CHORDS = [[62, 66, 69], [57, 61, 64], [59, 62, 66], [55, 59, 62]]
BASS = [38, 33, 35, 31]
BAR = 4 * BEAT
CH_LEN = 2 * BAR

out = np.zeros(N)


def env_adsr(n, a, d, s, r):
    e = np.ones(n) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = min(na, n)
    e[:na] = np.linspace(0, 1, na)
    if na + nd < n:
        e[na:na + nd] = np.linspace(1, s, nd)
    if nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def add(sig, start):
    i = int(start * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    out[i:j] += sig[:j - i]


rng = np.random.default_rng(3)
k = 0
start = 0.0
while start < DUR:
    ch = CHORDS[k % 4]
    n = int(CH_LEN * SR) + int(0.6 * SR)
    tt = np.arange(n) / SR
    # pad: sierras desafinadas suavizadas
    pad = np.zeros(n)
    for m in ch:
        for det in (-0.08, 0.0, 0.08):
            f = midi(m + 12) * 2 ** (det / 12)
            pad += np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)
    pad = np.convolve(pad, np.ones(30) / 30, mode="same")
    add(0.018 * pad * env_adsr(n, 0.8, 0.5, 0.8, 0.8), start)
    # bajo: corcheas
    for b in range(16):
        nb = int(BEAT / 2 * SR)
        tb = np.arange(nb) / SR
        f = midi(BASS[k % 4])
        s = np.sin(2 * np.pi * f * tb) + 0.25 * np.sin(2 * np.pi * 2 * f * tb)
        add(0.10 * s * env_adsr(nb, 0.005, 0.12, 0.3, 0.05), start + b * BEAT / 2)
    # arpegio pluck en semicorcheas (entra desde el 2º acorde)
    if k >= 1:
        notes = [ch[0] + 24, ch[1] + 24, ch[2] + 24, ch[1] + 24]
        for st in range(32):
            ns = int(0.35 * SR)
            ts = np.arange(ns) / SR
            f = midi(notes[st % 4])
            s = np.sin(2 * np.pi * f * ts) * np.exp(-ts * 14) + 0.3 * np.sin(2 * np.pi * 2 * f * ts) * np.exp(-ts * 22)
            add(0.035 * s, start + st * BEAT / 4)
    # hi-hat ligero a contratiempo y bombo suave en cada tiempo (desde el 2º acorde)
    if k >= 1:
        for bt in range(8):
            nh = int(0.05 * SR)
            hh = rng.standard_normal(nh) * np.exp(-np.arange(nh) / SR * 80)
            hh = np.diff(hh, prepend=0)
            add(0.03 * hh, start + bt * BEAT + BEAT / 2)
            nk = int(0.25 * SR)
            tk = np.arange(nk) / SR
            kick = np.sin(2 * np.pi * (55 + 90 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 12)
            add(0.12 * kick, start + bt * BEAT)
    start += CH_LEN
    k += 1

# fundidos y normalización
fade_in, fade_out = int(1.0 * SR), int(2.5 * SR)
out[:fade_in] *= np.linspace(0, 1, fade_in)
out[-fade_out:] *= np.linspace(1, 0, fade_out)
out /= np.max(np.abs(out)) + 1e-9
out *= 0.8
st = np.stack([out, np.roll(out, int(0.012 * SR))], axis=1)  # ligera amplitud estéreo
pcm = (st * 32767).astype(np.int16)

dest = sys.argv[2] if len(sys.argv) > 2 else os.path.join(AQUI, "audio", "musica.wav")
with wave.open(dest, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("Listo:", dest)
