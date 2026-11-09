# Video TikTok: Seguridad en escaleras (UNIPROTEC)

Estado: en preparación.

- `generar_video.py`: primer borrador **ilustrado** (descartado). Sirve de base para el
  pipeline de narración (ElevenLabs) + montaje vertical 1080x1920 con ffmpeg.
- La versión final será **fotográfica/realista**, máx. 40 s, colores UNIPROTEC
  (#0086FF, #0B2A5B, #FFA400, blanco) y cierre con el logotipo original.

## Guion propuesto (~35 s)

¿Esta escalera está colocada de forma segura? Revisemos tres puntos clave.
Uno: inclinación. Aplica la regla cuatro a uno: por cada cuatro metros de longitud de trabajo,
separa la base un metro de la pared.
Dos: extensión. Para acceder a un techo o plataforma, los largueros deben sobresalir al menos
noventa centímetros.
Tres: uso. Sube de frente a la escalera, sujétate siempre con al menos una mano y no cargues
objetos. Eleva tus herramientas con una cuerda.
La prevención comienza con la capacitación. UNIPROTEC. Innovando en capacitación.

## Datos en pantalla (verificar numeración en eCFR antes de publicar)

| Punto | Dato | Referencia |
|---|---|---|
| Inclinación | Regla 4:1 (≈75°) | OSHA 29 CFR 1926.1053(b)(5)(i) |
| Extensión | ≥ 90 cm (3 ft) sobre el nivel de acceso | OSHA 1926.1053(b)(1) |
| Uso | De frente, al menos una mano, sin cargar objetos | OSHA 1926.1053(b)(20)–(22) |

## Uso

    python3 generar_video.py            # usa ElevenLabs si la API key es válida
    python3 generar_video.py --sin-voz  # borrador sin voz
