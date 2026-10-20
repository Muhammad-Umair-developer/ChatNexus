"""
Tests for the core LLM logic.
"""
from src.llm import get_chat_model, SYSTEM_PROMPT
from src.config import LLM_MODEL, TEMPERATURE

def test_system_prompt_integrity():
    """Ensure the system prompt hasn't been accidentally cleared or shortened."""
    assert isinstance(SYSTEM_PROMPT, str)
    assert len(SYSTEM_PROMPT) > 50
    assert "ChatNexus" in SYSTEM_PROMPT

def test_get_chat_model_configuration():
    """Verify the AI model initializes with the exact parameters defined in config.py."""
    model = get_chat_model()
    
    # Verify LangChain applied the temperature and model name correctly
    assert model.temperature == TEMPERATURE
    assert model.model == LLM_MODEL  # LangChain Google GenAI uses .model, not .model_name