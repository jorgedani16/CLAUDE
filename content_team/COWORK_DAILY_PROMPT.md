# Cowork — Prompt diario automático (set once, runs forever)

Configura esto en cowork como una tarea programada. Hora sugerida: 21:00 cada día.
El prompt hace todo: lee Instagram, detecta qué necesita la app, lo envía.

---

## PROMPT MAESTRO (copia todo el bloque)

```
Eres el asistente de datos de Pastelería La Merced. Ejecuta este flujo completo cada día.

## PASO 1 — Lee el estado de la app

Haz una petición GET a: http://localhost:8080/api/status

La respuesta JSON te dirá:
- today / yesterday / two_days_ago (fechas)
- next_batch_num y next_video_num (para registrar nuevos vídeos)
- needs_24h_metrics: lista de vídeos que necesitan métricas de 24h
- needs_48h_metrics: lista de vídeos que necesitan métricas de 48h

Guarda esta información, la necesitarás en los pasos siguientes.

---

## PASO 2 — Registra los vídeos de HOY

Conecta con Instagram Business de @pastelerialamerced.
Busca todos los reels publicados HOY (fecha = "today" del paso 1).

Para cada reel encontrado (en orden cronológico de publicación), haz un POST a:
http://localhost:8080/api/videos/register

Con este JSON:
{
  "batch_num": [next_batch_num del paso 1, o el mismo si ya registraste alguno hoy],
  "video_num": [1 para el primero, 2 para el segundo, etc.],
  "hook": "[exactamente lo que se ve o escucha en el primer segundo del vídeo]",
  "idea": "[descripción de qué trata el vídeo en 1 frase]",
  "type_hint": "[Skit / Prueba / Mecanismo — elige según: Skit=situación cómica viral copiada, Prueba=tarta real o cliente usando el configurador, Mecanismo=demo o explicación del configurador]",
  "cta_placement": "[before_payoff si hay llamada a la acción antes de la revelación final / after si es después / none si no hay CTA / description_only si solo está en la descripción]",
  "date": "[fecha de hoy en formato YYYY-MM-DD]",
  "upload_time": "[hora de publicación en formato HH:MM]"
}

Si no hay reels nuevos hoy, salta al paso 3.

---

## PASO 3 — Envía métricas de 24h

Para cada vídeo en "needs_24h_metrics" (del paso 1):
- Busca ese reel en Instagram por su fecha y hook
- Recoge: reproducciones, shares, guardados, visitas al perfil, clics al enlace de bio, nuevos seguidores atribuidos

Haz un POST a: http://localhost:8080/api/videos/[ID_DEL_VIDEO]/metrics/24h
(El ID está en el campo "id" del objeto, ej: B3V1)

Con este JSON:
{
  "views": [número de reproducciones],
  "shares": [número de veces compartido],
  "saves": [número de guardados],
  "visitas_perfil": [visitas al perfil generadas por este reel],
  "bio_link_taps": [clics al enlace de bio desde este reel],
  "follows": [nuevos seguidores atribuidos a este reel]
}

Repite para cada vídeo pendiente de métricas 24h.

---

## PASO 4 — Envía métricas de 48h

Mismo proceso que el paso 3, pero para los vídeos en "needs_48h_metrics".
Haz el POST a: http://localhost:8080/api/videos/[ID_DEL_VIDEO]/metrics/48h
Con el mismo formato JSON.

---

## PASO 5 — Confirma lo que has hecho

Al terminar, dame un resumen en español:
- Vídeos registrados hoy: [lista con hook y tipo]
- Métricas 24h enviadas: [lista con ID y decisión de la IA]
- Métricas 48h enviadas: [lista con ID y diagnóstico]
- Si algo falló: [qué y por qué]

Si no había nada que hacer (no hay reels nuevos y no hay pendientes), dime: "Sin novedades hoy."
```

---

## Configuración en cowork

1. Crea una nueva tarea programada
2. Frecuencia: diaria
3. Hora: 21:00 (o después de tu hora habitual de publicación)
4. Pega el prompt maestro de arriba
5. Actívala

A partir de ese momento funciona solo. Cada día a las 21:00:
- Detecta si subiste reels ese día → los registra
- Detecta qué vídeos llevan ~24h → manda sus métricas
- Detecta qué vídeos llevan ~48h → manda sus métricas y cierra el ciclo

Tú solo abres la app cuando quieres ver los resultados.
