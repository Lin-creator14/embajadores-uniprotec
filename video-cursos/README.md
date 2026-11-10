# Video promocional UNIPROTEC · Cursos

Liderazgo Proactivo · Growth Mindset · LEGO® SERIOUS PLAY®
Vertical 1080×1920, ~36,5 s, tomas reales del taller (`clips/toma1–6.mov`).

**Resultado:** `salida/uniprotec_cursos_promo.mp4`

## Estructura

| Tiempo | Contenido |
|---|---|
| 0–3 s | Gancho: «¿Tu equipo está listo para el siguiente nivel?» |
| 3–8 s | UNIPROTEC: capacitación que se vive |
| 8–15 s | Curso 01 · Liderazgo Proactivo (Anticipación · Inspiración · Mejores decisiones) |
| 15–22 s | Curso 02 · Growth Mindset (Aprender · Adaptarse · Superar retos) |
| 22–29 s | Curso 03 · LEGO® SERIOUS PLAY® (Ideas · Estrategia · Trabajo en equipo) |
| 29–32 s | Llamada a la acción + ventasoficial@uniprotec.net |
| 32–36 s | Logotipo original + cursos + correo |

## Narración (ElevenLabs)

¿Tu equipo está listo para el siguiente nivel? En UNIPROTEC convertimos la capacitación en una experiencia
que se vive. Liderazgo Proactivo: líderes que se anticipan, inspiran y toman mejores decisiones. Growth Mindset:
una mentalidad de crecimiento para aprender, adaptarse y superar cualquier reto. LEGO Serious Play: ideas y
estrategias que se construyen con las manos, en equipo. Lleva estos cursos a tu empresa. Escríbenos hoy.
UNIPROTEC. Innovando en capacitación.

## Tratamiento de imagen

Los clips recibidos son de 478×850 (comprimidos). Se escalan a 1080×1920 con Lanczos, reducción de ruido
(hqdn3d), nitidez y corrección de color. Con los archivos originales del teléfono la nitidez sería mayor.

## Privacidad: rostros difuminados

`promo.py` detecta los rostros en cada fotograma con YuNet (OpenCV Zoo, licencia Apache-2.0,
`modelos/face_detection_yunet_2023mar.onnx`) y los difumina con una elipse suave estable en el tiempo.
Para desactivarlo: `DIFUMINAR_ROSTROS = False`. Umbral de confianza: `UMBRAL`.

## Generar

    python3 promo.py --preview
    python3 promo.py
