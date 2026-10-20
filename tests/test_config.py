"""
Tests for the configuration module.
"""
import os
import pytest
import importlib
from src import config

def test_app_constants():
    """Verify that critical enterprise branding and model settings are not accidentally changed."""
    assert config.APP_NAME == "ChatNexus"
    assert config.LLM_MODEL == "gemini-2.5-flash"
    assert config.TEMPERATURE == 0.7

def test_missing_api_key_raises_error(monkeypatch, mocker):
    """
    Simulate a production environment missing the API key.
    """
    # 1. Patch load_dotenv at the source library so the reload cannot fetch the real one
    mocker.patch("dotenv.load_dotenv")
    
    # 2. Temporarily remove the key from the system environment
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    
    # 3. Assert that reloading the config file triggers our specific EnvironmentError
    with pytest.raises(EnvironmentError, match="GOOGLE_API_KEY is missing"):
        importlib.reload(config)