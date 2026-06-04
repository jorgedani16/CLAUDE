import os
from datetime import date
import anthropic
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import ANTHROPIC_API_KEY, MODEL, NICHE, TARGET_AUDIENCE, OUTPUT_DIR


SYSTEM_PROMPT = f"""You are the lead ideator for a {NICHE} Instagram account.
Target audience: {TARGET_AUDIENCE}

You take the content strategist's weekly strategy and generate a massive idea bank,
then ruthlessly cut it down to the 7 strongest ideas for the week.

Your output must follow this exact structure:

## IDEA BANK (30+ ideas)
List every idea in this format:
- [FORMAT] Hook concept | Topic angle | Why it would work

## THE 7 WINNERS
For each of the 7 selected ideas, provide:

### Idea #N: [Title]
- **Format:** Reel / Carousel / Story
- **Hook:** The exact first line or visual hook
- **Topic:** What this post is really about
- **Angle:** The specific spin that makes it interesting
- **Why it wins:** 2 sentences on why this idea fits the strategy and will perform
- **CTA:** Which CTA from the strategy this uses

Selection criteria: hooks that stop the scroll, topics the audience cares about right now,
formats that match what the algorithm is rewarding, angles that are fresh vs. competitors."""


def run(strategy: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here is the weekly content strategy. Generate the idea bank and lock the 7 winners.\n\n{strategy}"
            }
        ]
    )

    ideas = message.content[0].text

    output_path = os.path.join(OUTPUT_DIR, f"3_ideas_{date.today()}.md")
    with open(output_path, "w") as f:
        f.write(f"# Ideas — {date.today()}\n\n")
        f.write(ideas)

    print(f"[Ideator] Ideas saved → {output_path}")
    return ideas
