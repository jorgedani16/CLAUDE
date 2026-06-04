import os
from datetime import date
import anthropic
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import ANTHROPIC_API_KEY, MODEL, NICHE, BRAND_VOICE, TARGET_AUDIENCE, OUTPUT_DIR


SYSTEM_PROMPT = f"""You are the content strategist for a {NICHE} Instagram account.
Brand voice: {BRAND_VOICE}
Target audience: {TARGET_AUDIENCE}

You read the Data Analyst's brief and build the weekly content strategy.
You decide WHAT we post, HOW OFTEN, in WHAT FORMAT, and with WHICH CTA.

Your output must include these exact sections:

1. WEEKLY THEME — one overarching message/angle for the week
2. CONTENT MIX — breakdown of post types (e.g., 3 Reels, 2 Carousels, 2 Stories)
3. WINNING CTAs THIS WEEK — 3 CTAs ranked by expected conversion, with context on when to use each
4. TOPICS TO HIT — list of 5-7 general topic areas the ideator should explore
5. TOPICS TO AVOID — based on analyst data, what we're staying away from
6. FORMAT RULES — specific format/style rules for this week (hook style, video length, caption length)
7. STRATEGY RATIONALE — 3-4 sentences on why this strategy fits the data and the audience right now

Be decisive. Give the ideator clear constraints to work within."""


def run(analyst_brief: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here is the Data Analyst's brief for this week. Build the content strategy.\n\n{analyst_brief}"
            }
        ]
    )

    strategy = message.content[0].text

    output_path = os.path.join(OUTPUT_DIR, f"2_content_strategy_{date.today()}.md")
    with open(output_path, "w") as f:
        f.write(f"# Content Strategy — {date.today()}\n\n")
        f.write(strategy)

    print(f"[Content Strategist] Strategy saved → {output_path}")
    return strategy
