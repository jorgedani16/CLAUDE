import json
import os
from datetime import date
import anthropic
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import ANTHROPIC_API_KEY, MODEL, NICHE, OUTPUT_DIR, DATA_DIR


SYSTEM_PROMPT = f"""You are a sharp data analyst for a {NICHE} Instagram account.
Your job is to turn raw weekly metrics into a clear, actionable brief for the content team.

You analyze:
- Which posts won (and exactly WHY — hook, format, topic, CTA)
- Which posts died (and WHY — so we never repeat the mistake)
- What competitors are doing that's working
- Trends in reach, saves, shares, and DM leads

Output a structured brief with these exact sections:
1. WEEKLY SNAPSHOT — 3 bullet KPIs (reach, followers, DM leads)
2. WINNING HOOKS THIS WEEK — list each winning hook + what made it work
3. DEAD FORMATS / TOPICS — what to avoid this week
4. COMPETITOR INTEL — what's working for them and how we can adapt it
5. ALGORITHM SIGNALS — what the data says the algorithm rewarded this week
6. ANALYST RECOMMENDATION — top 3 directives for the content strategist

Be direct. No fluff. Use numbers. Flag anything that needs to change immediately."""


def run(metrics_path: str | None = None) -> str:
    if metrics_path is None:
        metrics_path = os.path.join(DATA_DIR, "metrics_input.json")

    with open(metrics_path) as f:
        metrics = json.load(f)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here are this week's Instagram metrics. Write the analyst brief.\n\n{json.dumps(metrics, indent=2)}"
            }
        ]
    )

    brief = message.content[0].text

    output_path = os.path.join(OUTPUT_DIR, f"1_analyst_brief_{date.today()}.md")
    with open(output_path, "w") as f:
        f.write(f"# Data Analyst Brief — {date.today()}\n\n")
        f.write(brief)

    print(f"[Data Analyst] Brief saved → {output_path}")
    return brief
