"""
Analyzes a week of Instagram data (entered from cowork or manually)
against La Merced's marketing plan and returns a structured report.
"""
import json
import re
import anthropic
import config as cfg


def analyze_week(data: dict) -> dict:
    """
    data: the structured cowork/manual Instagram data dict
    Returns: dict with summary, what_worked, on_track indicators, directives
    """
    client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)

    prompt = f"""Eres el Data Analyst del equipo de contenido de Pastelería La Merced (Valencia, España).
Tu trabajo es leer los datos de Instagram de esta semana y dar un veredicto claro sobre qué funcionó,
si el canal va por buen camino y qué hacer la semana siguiente.

PLAN DE MARKETING DE LA MERCED:
- North Star: ventas del configurador online por semana
- 3 tipos de reel: El Skit (viral puro, copiamos formato exacto), La Prueba (prueba social), El Mecanismo (demo del configurador)
- CTA siempre mid-video ANTES del payoff → enlace al configurador
- Métrica clave de Instagram: visitas de perfil por reel
- Si un reel no genera visitas de perfil, no funciona para vender

DATOS DE INSTAGRAM ESTA SEMANA:
{json.dumps(data, indent=2, ensure_ascii=False)}

Responde ÚNICAMENTE con JSON válido, sin texto antes ni después:
{{
  "resumen_semana": "2-3 frases describiendo la semana en Instagram",
  "norte": "BIEN|REGULAR|MAL",
  "norte_razon": "frase corta explicando por qué",
  "indicadores": {{
    "visitas_perfil_por_reel": {{"valor": "número o ?", "tendencia": "SUBE|BAJA|ESTABLE|DESCONOCIDO", "ok": true/false}},
    "followers_ganados": {{"valor": "número o ?", "tendencia": "SUBE|BAJA|ESTABLE|DESCONOCIDO", "ok": true/false}},
    "engagement_rate": {{"valor": "número% o ?", "tendencia": "SUBE|BAJA|ESTABLE|DESCONOCIDO", "ok": true/false}},
    "mejor_formato": {{"valor": "Skit|Prueba|Mecanismo|?", "ok": true/false}}
  }},
  "que_funciono": [
    {{"titulo": "...", "detalle": "..."}}
  ],
  "que_no_funciono": [
    {{"titulo": "...", "detalle": "..."}}
  ],
  "directrices_semana_siguiente": [
    {{"numero": 1, "accion": "..."}},
    {{"numero": 2, "accion": "..."}},
    {{"numero": 3, "accion": "..."}}
  ],
  "alerta": ""
}}
Si hay pocos datos, estima lo que puedas y marca los desconocidos claramente.
"""

    msg = client.messages.create(
        model=cfg.MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = msg.content[0].text.strip()
    # Strip markdown fences if present
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)
