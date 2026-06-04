"""
AI decisions for individual video tracking:
- Auto-categorize type, flag CTA, summarize, suggest improvement
- 24h decision: PUBLICA / ELIMINA / ESPERA
- 48h decision: PUBLICA / ELIMINA + diagnosis
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config as cfg
import anthropic


def analyze_registration(idea: str, hook: str, type_hint: str, cta_placement: str) -> dict:
    """On video registration: categorize, summarize, flag CTA, suggest improvement."""
    client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)

    cta_descriptions = {
        "before_payoff": "antes del payoff (correcto)",
        "after": "después del payoff (problema — llega tarde)",
        "none": "sin CTA (problema — falta)",
        "description_only": "solo en descripción (problema — no en vídeo)",
    }
    cta_desc = cta_descriptions.get(cta_placement, cta_placement)

    prompt = f"""Eres el analista de vídeos de Pastelería La Merced. Analiza este vídeo recién registrado.

DATOS DEL VÍDEO:
- Idea: {idea}
- Hook (primer segundo): {hook}
- Tipo indicado: {type_hint or 'no indicado — categoriza tú'}
- Placement del CTA: {cta_desc}

LOS 3 TIPOS:
- Skit: situación relatable → giro inesperado → configurador es el remate
- Prueba: pedido real / unboxing / reacción de cliente
- Mecanismo: grabación de pantalla del configurador

REGLA DEL CTA: siempre mid-video ANTES del payoff. Si no es así, es un problema.

Responde en JSON con exactamente estas claves:
{{
  "type": "Skit" | "Prueba" | "Mecanismo",
  "cta_flag": "correcto" | "problema",
  "cta_flag_reason": "por qué está bien o mal (1 frase)",
  "ai_summary": "qué hace este vídeo en 1 frase",
  "ai_improvement": "1 cosa concreta a mejorar o cambiar antes de publicar"
}}

Solo JSON, sin texto extra."""

    message = client.messages.create(
        model=cfg.MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    text = message.content[0].text.strip()
    # strip markdown code blocks if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def analyze_24h(video: dict) -> dict:
    """Given 24h metrics, decide PUBLICA / ELIMINA / ESPERA."""
    client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)

    m = video.get("metrics_24h", {})
    prompt = f"""Eres el analista de vídeos de Pastelería La Merced. Toma la decisión de 24h para este vídeo.

VÍDEO:
- ID: {video['id']}
- Tipo: {video['type']}
- Hook: {video['hook']}
- Resumen: {video['ai_summary']}

MÉTRICAS A LAS 24H:
- Views: {m.get('views', 0)}
- Shares: {m.get('shares', 0)}
- Saves: {m.get('saves', 0)}
- Visitas de perfil desde el reel: {m.get('visitas_perfil', 0)}
- Bio link taps: {m.get('bio_link_taps', 0)}
- Follows: {m.get('follows', 0)}

CRITERIO DE DECISIÓN:
- PUBLICA: el vídeo está funcionando bien, no hay que hacer nada
- ELIMINA: rendimiento muy bajo, el vídeo daña más de lo que ayuda, mejor borrarlo y re-intentar
- ESPERA: métricas mediocres pero no malas, dejar 24h más antes de decidir

La métrica más importante es visitas de perfil desde el reel (indica intención de compra).

Responde en JSON:
{{
  "decision": "PUBLICA" | "ELIMINA" | "ESPERA",
  "razon": "por qué (2 frases máximo)"
}}

Solo JSON."""

    message = client.messages.create(
        model=cfg.MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def analyze_48h(video: dict) -> dict:
    """Given 48h metrics (and 24h context), give final decision + diagnosis."""
    client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)

    m24 = video.get("metrics_24h", {})
    m48 = video.get("metrics_48h", {})

    prompt = f"""Eres el analista de vídeos de Pastelería La Merced. Decisión final a las 48h.

VÍDEO:
- ID: {video['id']}
- Tipo: {video['type']}
- Hook: {video['hook']}
- CTA placement: {video.get('cta_placement', '?')} — Flag: {video.get('cta_flag', '?')}
- Resumen: {video['ai_summary']}
- Sugerencia de mejora inicial: {video.get('ai_improvement', '?')}

MÉTRICAS 24H:
- Views: {m24.get('views', 0)} | Shares: {m24.get('shares', 0)} | Saves: {m24.get('saves', 0)}
- Visitas perfil: {m24.get('visitas_perfil', 0)} | Bio taps: {m24.get('bio_link_taps', 0)} | Follows: {m24.get('follows', 0)}
- Decisión 24h: {m24.get('decision', '?')}

MÉTRICAS 48H:
- Views: {m48.get('views', 0)} | Shares: {m48.get('shares', 0)} | Saves: {m48.get('saves', 0)}
- Visitas perfil: {m48.get('visitas_perfil', 0)} | Bio taps: {m48.get('bio_link_taps', 0)} | Follows: {m48.get('follows', 0)}

CRITERIO:
- PUBLICA: dejarlo vivo, sigue acumulando valor
- ELIMINA: borrarlo, el vídeo no funciona

Responde en JSON:
{{
  "decision_final": "PUBLICA" | "ELIMINA",
  "diagnostico": "qué falló exactamente y qué cambiar en el próximo vídeo similar (3-4 frases concretas)",
  "repetir": true | false,
  "repetir_razon": "si repetir: qué cambiar. si no: por qué no merece la pena"
}}

Solo JSON."""

    message = client.messages.create(
        model=cfg.MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    text = message.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())
