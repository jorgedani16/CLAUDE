import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5-20251001"

# Business — pre-filled for La Merced
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "Pastelería La Merced")
INSTAGRAM_HANDLE = os.getenv("INSTAGRAM_HANDLE", "@pastelerialamerced")
LOCATION = os.getenv("LOCATION", "Valencia, España")
WEBSITE = os.getenv("WEBSITE", "pastelerialamerced.es")
NICHE = os.getenv("NICHE", "Tartas personalizadas hechas a medida para bodas, cumpleaños, baby showers y eventos especiales. Diseño totalmente personalizado online. Recogida en Valencia.")
TARGET_AUDIENCE = os.getenv("TARGET_AUDIENCE", "Hombres y mujeres de 20 a 40 años en Valencia que tienen un evento próximo y buscan una tarta única y personalizada.")
BRAND_VOICE = os.getenv("BRAND_VOICE", "Directo, cercano, artesanal. Habla como un dueño de pastelería local que ama lo que hace. Sin corporativismo.")
MAIN_CTA = os.getenv("MAIN_CTA", "Diseña la tuya ahora — visita el enlace en la descripción ■")

# API integrations
GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
SEARCH_CONSOLE_SITE_URL = os.getenv("SEARCH_CONSOLE_SITE_URL", "https://pastelerialamerced.es")
SQUARESPACE_API_KEY = os.getenv("SQUARESPACE_API_KEY", "")
