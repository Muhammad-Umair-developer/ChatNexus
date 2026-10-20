"""
config.py

Centralized configuration and environment management for ChatNexus.
Follows the 12-Factor App methodology by strictly separating configuration 
(like API keys and model parameters) from application code.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables from a local .env file during development.
# In production, these should be injected by the deployment environment (e.g., Docker/Kubernetes).
load_dotenv()

# --- Application Constants ---
APP_NAME = "ChatNexus"
APP_ICON = "⚡"

# --- LLM Configuration ---
LLM_MODEL = "gemini-2.5-flash"
TEMPERATURE = 0.7  # 0.0 = deterministic/strict, 1.0 = highly creative

# --- Logging Configuration ---
# Configures a dual-handler logging system. 
# 1. FileHandler: Persists logs to 'nexus.log' for auditing and debugging.
# 2. StreamHandler: Outputs logs to the terminal for live monitoring.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler("nexus.log"), 
        logging.StreamHandler()
    ]
)

# Instantiate a dedicated logger for the application
logger = logging.getLogger("ChatNexus")

# --- Environment Validation ---
# Fail fast: Ensure critical secrets are present before the application attempts to boot.
if not os.getenv("GOOGLE_API_KEY"):
    logger.critical("Boot sequence halted: GOOGLE_API_KEY is missing from the environment.")
    raise EnvironmentError(
        "GOOGLE_API_KEY is missing. Please add it to your .env file or environment variables."
    )