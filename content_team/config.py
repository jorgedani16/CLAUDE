import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = "claude-haiku-4-5-20251001"  # cheapest model

NICHE = os.getenv("NICHE", "local business / service")
BRAND_VOICE = os.getenv("BRAND_VOICE", "direct, confident, results-driven")
TARGET_AUDIENCE = os.getenv("TARGET_AUDIENCE", "local homeowners and small business owners")
INSTAGRAM_HANDLE = os.getenv("INSTAGRAM_HANDLE", "@yourbrand")
COMPETITORS = os.getenv("COMPETITORS", "").split(",")  # comma-separated handles

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
