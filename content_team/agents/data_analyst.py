import json
import os
from datetime import date
import anthropic
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config as cfg


SYSTEM_PROMPT = """Eres el Analista de Datos del equipo de contenido de Pastelería La Merced.
Tu trabajo: convertir los datos de la semana en un brief claro y accionable.

REGLAS DEL PLAN DE MARKETING QUE CONOCES:
- North Star metric: Ventas del configurador por semana
- Las 5 métricas que importan: ventas configurador/semana, visitas perfil/reel, conv. rate web, leads WhatsApp, reseñas Google
- CTA siempre: "visita el enlace en la descripción" → configurador. DEBE aparecer mid-video antes del payoff.
- Caption fórmula: Línea 1 = deseo/tensión (NUNCA descripción del vídeo). Líneas 2-3 = punto corto. Última línea = "Diseña la tuya ahora — link en bio ■"
- Fórmula ganadora: iterar 20 veces antes de cambiar. No pienses en formato, piensa en resultados.
- Señales de alarma: visitas perfil bajando 3 semanas seguidas, >40% menciona precio en encuesta, ventas=0 en semana 3+

FORMATO DE SALIDA — usa EXACTAMENTE estas secciones:

# BRIEF SEMANA [fecha]

## 1. NORTH STAR
- Ventas configurador esta semana: X (vs semana anterior: Y → Δ Z%)
- Conv. rate configurador: X%
- Leads WhatsApp: X (estos deben BAJAR con el tiempo)

## 2. CONTENIDO QUE GANÓ
[Para cada post top: tipo (Skit/Prueba/Mecanismo), hook, métricas, POR QUÉ funcionó]

## 3. CONTENIDO QUE MURIÓ
[Qué falló y exactamente por qué — ¿falló el hook? ¿Formato equivocado? ¿Sin CTA mid-video?]

## 4. SEÑALES DEL ALGORITMO
[Qué premió Instagram esta semana basándote en los datos]

## 5. INTEL DE COMPETIDORES
[Qué hicieron los competidores que funcionó + cómo adaptarlo]

## 6. TRÁFICO WEB (GA4 + SEARCH CONSOLE)
[Métricas web clave, fuentes de tráfico top, búsquedas top, tasa de conversión configurador]

## 7. VENTAS SQUARESPACE
[Pedidos, ingresos, valor medio de pedido esta semana]

## 8. DIRECTIVAS PARA EL ESTRATEGA
- Directiva 1: [instrucción específica]
- Directiva 2: [instrucción específica]
- Directiva 3: [instrucción específica]

## 9. SEÑALES DE ALARMA
[Marca cualquier señal de alarma del plan: visitas perfil bajando 3 semanas, >40% precio en encuesta, ventas=0 en semana 3+]

Sé directo. Sin relleno. Usa números. Señala todo lo que necesite cambio inmediato."""


def run(instagram_metrics: dict, ga4_data: dict, sc_data: dict, sq_data: dict) -> str:
    today = date.today().isoformat()

    ga4_text = json.dumps(ga4_data, indent=2, ensure_ascii=False)
    sc_text = json.dumps(sc_data, indent=2, ensure_ascii=False)
    sq_text = json.dumps(sq_data, indent=2, ensure_ascii=False)
    ig_text = json.dumps(instagram_metrics, indent=2, ensure_ascii=False)

    if "error" in ga4_data:
        ga4_text = f"DATOS NO DISPONIBLES — {ga4_data['error']}"
    if "error" in sc_data:
        sc_text = f"DATOS NO DISPONIBLES — {sc_data['error']}"
    if "error" in sq_data:
        sq_text = f"DATOS NO DISPONIBLES — {sq_data['error']}"

    user_message = f"""Fecha de análisis: {today}

=== MÉTRICAS INSTAGRAM (manual) ===
{ig_text}

=== DATOS GA4 (últimos 7 días) ===
{ga4_text}

=== DATOS SEARCH CONSOLE (últimos 7 días) ===
{sc_text}

=== DATOS SQUARESPACE (últimos 7 días) ===
{sq_text}

Escribe el brief completo del analista usando exactamente las secciones del formato."""

    client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=cfg.MODEL,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    brief = message.content[0].text

    os.makedirs(str(cfg.OUTPUT_DIR), exist_ok=True)
    output_path = os.path.join(str(cfg.OUTPUT_DIR), f"1_analyst_brief_{today}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(brief)

    print(f"[Data Analyst] Brief guardado → {output_path}")
    return brief
