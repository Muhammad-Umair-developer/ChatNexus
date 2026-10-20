import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

APP_NAME = "ChatNexus"
APP_ICON = "⚡"
LLM_MODEL = "gemini-2.5-flash"  # High speed, free tier available
TEMPERATURE = 0.7

# Validate that the API key was loaded
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY is missing from .env. Please check your file.")