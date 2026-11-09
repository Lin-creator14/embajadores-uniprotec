# Video TikTok: Seguridad en escaleras (UNIPROTEC)

Video vertical 9:16 (1080×1920), ~39,5 s, estilo realista con fotografías reales,
narración en español (ElevenLabs), datos técnicos y referencias OSHA sincronizados con la voz,
colores institucionales y cierre con el logotipo original.

**Resultado:** `salida/escalera_uniprotec_tiktok.mp4`

## Generar

    python3 video_realista.py            # render completo
    python3 video_realista.py --preview  # fotogramas de muestra

Requiere Python 3 + Pillow y ffmpeg.

## Guion (narración)

¿Esta escalera está colocada de forma segura? Revisemos tres puntos clave.
Uno: inclinación. Aplica la regla cuatro a uno: por cada cuatro metros de longitud de trabajo,
separa la base un metro de la pared.
Dos: extensión. Para acceder a un techo o plataforma, los largueros deben sobresalir al menos
noventa centímetros.
Tres: uso. Sube de frente a la escalera, sujétate siempre con al menos una mano y no cargues
objetos. Eleva tus herramientas con una cuerda.
La prevención comienza con la capacitación. UNIPROTEC. Innovando en capacitación.

Voz: ElevenLabs, modelo `eleven_multilingual_v2`, voz base "Eric". Tiempos por carácter en
`audio/alineacion.json` (se usan para sincronizar subtítulos y fichas).

## Datos en pantalla

| Punto | Dato | Referencia |
|---|---|---|
| Inclinación | Regla 4:1 (base a ¼ de la longitud, ≈75°) | OSHA 29 CFR 1926.1053(b)(5)(i) |
| Extensión | ≥ 90 cm (3 ft) sobre el nivel de acceso | OSHA 29 CFR 1926.1053(b)(1) |
| Uso | De frente, al menos una mano, sin cargar objetos | OSHA 29 CFR 1926.1053(b)(20)–(22) |

> Verificar la numeración de (b)(20)–(22) en eCFR antes de publicar.

## Colores

Azul `#0086FF` · Azul oscuro `#0B2A5B` · Naranja `#FFA400` · Blanco.

## Créditos de fotografías (CC BY 2.0 — incluir en la descripción de la publicación)

- "Raclin Extension Ladder" — Collin Anderson — https://www.flickr.com/photos/7852439@N07/2913096806
- "Desert View Watchtower Roof Replacement Project" (2 fotos) — Grand Canyon NPS —
  https://www.flickr.com/photos/50693818@N08/40145895215 · https://www.flickr.com/photos/50693818@N08/41038817621
- "Sledge hammer at fifteen feet." — General Wesc — https://www.flickr.com/photos/35518575@N00/114389023
- Foto de vivaiquique — https://www.flickr.com/photos/56518546@N07/8001687454
- "Beam work" — OregonDOT — https://www.flickr.com/photos/28364885@N02/7415281734
- "Ribbon Cutting Ceremony - Kitgum High School" — US Army Africa — https://www.flickr.com/photos/36281822@N08/4054569981

Licencia: https://creativecommons.org/licenses/by/2.0/ — las fotos se recortaron y se les
añadieron gráficos. Detalle en `fotos/creditos.json`.

Texto sugerido para la descripción de TikTok:

    Fotos: Collin Anderson, Grand Canyon NPS, General Wesc, vivaiquique, OregonDOT,
    US Army Africa (CC BY 2.0, Flickr). Ref.: OSHA 29 CFR 1926.1053.

## Archivos anteriores

`generar_video.py` es el primer borrador ilustrado (descartado).
