import os
import logging
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

APP_NAME = "ChatNexus"
APP_ICON = "⚡"
LLM_MODEL = "gemini-2.5-flash"
TEMPERATURE = 0.7

# Configure Enterprise Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("nexus.log"), 
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ChatNexus")

# Validate that the API key was loaded
if not os.getenv("GOOGLE_API_KEY"):
    logger.error("Startup failure: GOOGLE_API_KEY is missing from .env.")
    raise ValueError("GOOGLE_API_KEY is missing from .env. Please check your file.")