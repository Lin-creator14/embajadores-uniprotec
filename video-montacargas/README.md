# Video UNIPROTEC: Inspección del montacargas antes de operar

Vertical 9:16, máx. 40 s. Estado: narración, música y montaje listos; faltan los 6 clips de video (ElevenLabs Image & Video, 9:16).

- `audio/narracion.mp3`: voz ElevenLabs (eleven_multilingual_v2, voz "Eric", velocidad 1.2), 39,1 s.
- `audio/alineacion.json`: tiempos por carácter para sincronizar subtítulos y textos.

## Tiempos de la narración (s)

| Bloque | Inicio |
|---|---|
| Antes de encender… inspección previa | 0,0 |
| ¿Sabías que…? | 5,3 |
| Primero, revisa las llantas | 9,1 |
| Después, inspecciona las horquillas | 13,7 |
| Comprueba frenos, dirección, luces, alarma | 20,2 |
| Si detectas alguna falla… repórtala | 26,0 |
| Recuerda: operar de forma segura… | 31,5 |
| ¡Capacita a tu equipo! | 35,0 |
| UNIPROTEC. Innovando en capacitación | 36,6 (fin 39,1) |

## Montaje

1. Copia los clips como `clips/escena1.mp4` … `clips/escena6.mp4`.
2. `python3 montar_video.py --preview` para revisar fotogramas; ajusta `MARCAS` (círculos/flechas) si hace falta.
3. `python3 montar_video.py` → `salida/montacargas_uniprotec.mp4` (~39,7 s).

- `musica.py` sintetiza la música de fondo (`audio/musica.mp3`), sin derechos de terceros.
- Referencias en pantalla: OSHA 29 CFR 1910.178(q)(7) (inspección diaria antes de poner en servicio) y
  1910.178(p)(1) (equipo defectuoso fuera de servicio hasta su reparación). Verificar antes de publicar.
