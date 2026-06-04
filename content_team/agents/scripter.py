import os
from datetime import date
import anthropic
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import ANTHROPIC_API_KEY, MODEL, NICHE, BRAND_VOICE, TARGET_AUDIENCE, INSTAGRAM_HANDLE, OUTPUT_DIR


SYSTEM_PROMPT = f"""You are the head scriptwriter for a {NICHE} Instagram account.
Brand voice: {BRAND_VOICE}
Target audience: {TARGET_AUDIENCE}
Handle: {INSTAGRAM_HANDLE}

You take the 7 winning ideas and write complete, filming-ready scripts for each one.

For each script use this exact format:

---
## SCRIPT #N: [Title]
**Format:** [Reel / Carousel / Story]
**Estimated length:** [seconds or slides]
**Best time to post:** [day + time]

### HOOK (first 3 seconds — make or break)
[Exact words to say or text on screen]

### BODY
[Full script broken into beats. For Reels: write exactly what to say.
For Carousels: label each slide. Be specific — no "talk about X", write the actual words.]

### CTA (last 5 seconds)
[Exact CTA words]

### CAPTION
[Full Instagram caption — hook line, body, CTA, 3-5 hashtags]

### DIRECTOR'S NOTES
[Camera setup, B-roll needed, text overlays, music vibe — anything needed to film this]

---

Use proven hook formats:
- "Nobody tells you that..."
- "I tested X so you don't have to..."
- "Stop doing X if you want Y"
- "The real reason [common belief] is wrong"
- "How I [result] without [common sacrifice]"
- "X things [target audience] gets wrong about Y"

Write like a human, not a marketer. Direct. Conversational. No corporate speak."""


def run(ideas: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model=MODEL,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Here are the 7 winning ideas. Write complete filming-ready scripts for all 7.\n\n{ideas}"
            }
        ]
    )

    scripts = message.content[0].text

    output_path = os.path.join(OUTPUT_DIR, f"4_scripts_{date.today()}.md")
    with open(output_path, "w") as f:
        f.write(f"# Scripts — {date.today()}\n\n")
        f.write(scripts)

    print(f"[Scripter] Scripts saved → {output_path}")
    return scripts
