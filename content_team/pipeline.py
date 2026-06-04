#!/usr/bin/env python3
"""
Digital Content Team — Weekly Pipeline
Run this every Monday morning after filling in data/metrics_input.json

Usage:
    python pipeline.py                    # full run
    python pipeline.py --from strategist  # resume from a specific agent
    python pipeline.py --only analyst     # run only one agent
"""

import argparse
import os
import sys
from datetime import date

from config import ANTHROPIC_API_KEY, OUTPUT_DIR
from agents import data_analyst, content_strategist, ideator, scripter, publishing_manager


AGENTS = ["analyst", "strategist", "ideator", "scripter", "publisher"]


def find_latest_output(prefix: str) -> str | None:
    files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(prefix)]
    if not files:
        return None
    files.sort(reverse=True)
    path = os.path.join(OUTPUT_DIR, files[0])
    with open(path) as f:
        return f.read()


def run_pipeline(start_from: str = "analyst", only: str | None = None):
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set. Add it to your .env file.")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = date.today()
    print(f"\n{'='*60}")
    print(f"  CONTENT TEAM PIPELINE — {today}")
    print(f"{'='*60}\n")

    agents_to_run = [only] if only else AGENTS[AGENTS.index(start_from):]

    brief = strategy = ideas = scripts = None

    if "analyst" in agents_to_run:
        print("▶ Running: Data Analyst")
        brief = data_analyst.run()
        print()
    else:
        brief = find_latest_output("1_analyst_brief")

    if "strategist" in agents_to_run:
        if not brief:
            print("ERROR: No analyst brief found. Run analyst first.")
            sys.exit(1)
        print("▶ Running: Content Strategist")
        strategy = content_strategist.run(brief)
        print()
    else:
        strategy = find_latest_output("2_content_strategy")

    if "ideator" in agents_to_run:
        if not strategy:
            print("ERROR: No strategy found. Run strategist first.")
            sys.exit(1)
        print("▶ Running: Ideator")
        ideas = ideator.run(strategy)
        print()
    else:
        ideas = find_latest_output("3_ideas")

    if "scripter" in agents_to_run:
        if not ideas:
            print("ERROR: No ideas found. Run ideator first.")
            sys.exit(1)
        print("▶ Running: Scripter")
        scripts = scripter.run(ideas)
        print()
    else:
        scripts = find_latest_output("4_scripts")

    if "publisher" in agents_to_run:
        if not scripts or not strategy:
            print("ERROR: Missing scripts or strategy. Run earlier agents first.")
            sys.exit(1)
        print("▶ Running: Publishing Manager")
        publishing_manager.run(scripts, strategy)
        print()

    print(f"{'='*60}")
    print(f"  DONE. All outputs saved to: {OUTPUT_DIR}/")
    print(f"{'='*60}\n")
    print("Next steps:")
    print("  1. Review scripts in 4_scripts_*.md")
    print("  2. Film your content")
    print("  3. Check publishing plan in 5_publishing_plan_*.md")
    print("  4. Post and monitor\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the weekly content team pipeline")
    parser.add_argument(
        "--from", dest="start_from", default="analyst",
        choices=AGENTS,
        help="Start pipeline from this agent (skips earlier agents, loads their saved output)"
    )
    parser.add_argument(
        "--only", choices=AGENTS,
        help="Run only this single agent"
    )
    args = parser.parse_args()
    run_pipeline(start_from=args.start_from, only=args.only)
