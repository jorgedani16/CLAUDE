import os
from datetime import date, timedelta
import anthropic
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import config as cfg


SYSTEM_PROMPT = """Eres el Director de Publicación del equipo de contenido de Pastelería La Merced.
Tu trabajo: crear el plan de publicación semanal basado en la agenda exacta del plan de marketing.

LA AGENDA SEMANAL EXACTA QUE SIGUES:
- LUNES: Reel Skit + 2-3 stories BTS + CTA con resultado story + anotar métricas reel anterior
- MARTES: Reel Prueba + 2-3 stories BTS + revisar DMs de ManyChat
- MIÉRCOLES: Reel Mecanismo + 2-3 stories BTS + CTA con resultado story
- JUEVES: Reel Skit + 2-3 stories BTS + story poll activación → ManyChat trigger "¿Tienes un evento próximo?"
- VIERNES: Reel Prueba o Mecanismo + 2-3 stories BTS + CTA con resultado + anotar ventas semana
- SÁBADO: Reel Skit (el mejor de la semana o nuevo) + recap semanal tartas → highlights + quiénes somos repost
- DOMINGO: planificar próxima semana + revisar Clarity 15min + descansar

FRANJA HORARIA: 18:00-20:00 (mejor franja para Valencia)

REGLAS ABSOLUTAS:
- Mínimo diario no negociable: 1 Reel publicado · 2 Stories BTS · Métricas anotadas
- ManyChat: keyword TARTA activa en todos los reels. Story poll jueves.

TU OUTPUT — usa EXACTAMENTE este formato:

## AGENDA SEMANAL

### LUNES [fecha]
**REEL:** [Script #N título — Skit]
**HORA:** 18:00-20:00 (mejor franja para Valencia)
**STORIES:**
  - 2-3x BTS del proceso del día (raw, sin editar)
  - CTA con resultado: "[texto exacto para la story]"
**MÉTRICA A ANOTAR:** visitas de perfil del reel de ayer

[repetir para cada día con su contenido específico de los guiones]

## CHECKLIST MANYCHAT SEMANAL
- [ ] Trigger 1 activo: keyword TARTA en todos los reels publicados
- [ ] Trigger 2 (jueves): story poll "¿Tienes un evento próximo?" programada
- [ ] Revisar DMs automáticos el martes: ¿cuántos comentaron TARTA? ¿cuántos clicaron?
- [ ] Welcome message activo para nuevos seguidores

## CHECKLIST GO-LIVE
[Para cada reel: checklist de verificación de publicación correcta]

## CHECKLIST DM FUNNEL
- [ ] Link en bio apunta al configurador
- [ ] Respuesta template para nuevos DMs lista
- [ ] Keyword TARTA activa en ManyChat

## SEÑALES DE ALARMA A REVISAR ESTA SEMANA
[3 señales de alarma del plan a vigilar: visitas perfil bajando 3 semanas, >40% menciona precio, ventas=0 semana 3+]

## MÍNIMO DIARIO NO NEGOCIABLE
1 Reel publicado · 2 Stories BTS · Métricas anotadas

Asigna los scripts a los días correctos según el tipo (Skit→Lunes/Jueves/Sábado, Prueba→Martes/Viernes, Mecanismo→Miércoles/Viernes)."""


def run(scripts: str, strategy: str) -> str:
    today = date.today()
    # Find next Monday
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)

    week_dates = {
        "lunes": (next_monday).strftime("%d/%m"),
        "martes": (next_monday + timedelta(days=1)).strftime("%d/%m"),
        "miercoles": (next_monday + timedelta(days=2)).strftime("%d/%m"),
        "jueves": (next_monday + timedelta(days=3)).strftime("%d/%m"),
        "viernes": (next_monday + timedelta(days=4)).strftime("%d/%m"),
        "sabado": (next_monday + timedelta(days=5)).strftime("%d/%m"),
        "domingo": (next_monday + timedelta(days=6)).strftime("%d/%m"),
    }

    client = anthropic.Anthropic(api_key=cfg.ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=cfg.MODEL,
        max_tokens=3500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Aquí están los guiones aprobados y la estrategia. Crea el plan de publicación semanal.\n"
                    f"Fechas de la semana: Lunes {week_dates['lunes']}, Martes {week_dates['martes']}, "
                    f"Miércoles {week_dates['miercoles']}, Jueves {week_dates['jueves']}, "
                    f"Viernes {week_dates['viernes']}, Sábado {week_dates['sabado']}, Domingo {week_dates['domingo']}.\n\n"
                    f"## GUIONES\n{scripts}\n\n## ESTRATEGIA\n{strategy}"
                ),
            }
        ],
    )

    plan = message.content[0].text

    os.makedirs(str(cfg.OUTPUT_DIR), exist_ok=True)
    output_path = os.path.join(str(cfg.OUTPUT_DIR), f"5_publishing_plan_{today}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Plan de Publicación — {today}\n\n")
        f.write(plan)

    print(f"[Publishing Manager] Plan guardado → {output_path}")
    return plan
