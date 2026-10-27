"""
llm_service.py

LangChain orchestration for ChatNexus backend.
Configures Gemini 2.5 Flash / Flash Lite models with automatic quota resilience.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# Load environment variables across directory depths
current_dir = Path(__file__).resolve().parent
load_dotenv(current_dir / ".env")
load_dotenv(current_dir.parent / ".env")

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise EnvironmentError(
        "GOOGLE_API_KEY is not set in environment or .env file. "
        "Please provide a valid Google Gemini API key."
    )

# System persona for ChatNexus assistant
SYSTEM_PERSONA = (
    "You are ChatNexus, an advanced, professional AI engineering assistant. "
    "Provide clear, accurate, and structured responses. "
    "When explaining technical concepts or code, adhere to best practices."
)

# Use gemini-2.5-flash-lite by default to avoid the 20-req/day limit on free-tier preview models
PRIMARY_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash-lite")
FALLBACK_MODEL = "gemini-2.5-flash"


def create_chat_model(model_name: str) -> ChatGoogleGenerativeAI:
    """Factory helper to instantiate a ChatGoogleGenerativeAI instance."""
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.7,
        google_api_key=api_key,
    )


# Primary model for fast, quota-resilient responses
llm = create_chat_model(PRIMARY_MODEL)
# Secondary fallback model
fallback_llm = create_chat_model(FALLBACK_MODEL)


def generate_ai_response(chat_history: list, new_message: str) -> str:
    """
    Reconstructs conversation context and generates a synchronous AI response.

    Args:
        chat_history: List of past Message ORM models or dicts with 'role' and 'content'.
        new_message: The latest query from the user.

    Returns:
        str: Assistant response text.
    """
    messages = [SystemMessage(content=SYSTEM_PERSONA)]

    # Append past conversation turns
    for msg in chat_history:
        role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
        content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else "")

        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    # Append the new user prompt
    messages.append(HumanMessage(content=new_message))

    try:
        response = llm.invoke(messages)
    except Exception as exc:
        if "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc):
            response = fallback_llm.invoke(messages)
        else:
            raise exc

    return response.content