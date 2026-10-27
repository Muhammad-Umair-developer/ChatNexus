"""
llm.py

Handles all interactions with the Google Gemini LLM provider via LangChain.
Constructs prompt payloads with conversational history and handles token streaming.
"""

import time
from typing import Generator
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from src.config import LLM_MODEL, TEMPERATURE

# The core persona injected at the start of every API call.
SYSTEM_PROMPT = """You are ChatNexus, a highly capable and versatile AI assistant. 
You provide clear, accurate, and concise answers across all topics. 
Whether assisting with complex problem-solving, coding, writing, or general inquiries, 
your goal is to be exceptionally helpful, adaptable, and straightforward."""


def get_chat_model() -> ChatGoogleGenerativeAI:
    """
    Factory function to instantiate and configure the Google Gemini chat model.

    Returns:
        ChatGoogleGenerativeAI: The configured LangChain model object.
    """
    return ChatGoogleGenerativeAI(
        temperature=TEMPERATURE,
        model=LLM_MODEL,
    )


def stream_response(user_input: str) -> Generator[str, None, None]:
    """
    Builds the context window and streams the model's response back to the client.

    Args:
        user_input (str): The latest message from the user.

    Yields:
        str: Individual text chunks/tokens to create a real-time typing effect.
    """
    llm = get_chat_model()

    # 1. Initialize payload with the immutable system instructions
    formatted_messages = [SystemMessage(content=SYSTEM_PROMPT)]

    # 2. Append historical context without duplicating the latest user message
    # In app.py, the user prompt is committed to session_state.messages before stream_response is called.
    # We inspect session_state and slice off the latest entry if it matches user_input to avoid duplication.
    messages_history = st.session_state.messages
    if messages_history and messages_history[-1].get("content") == user_input:
        messages_history = messages_history[:-1]

    for msg in messages_history:
        if msg.get("role") == "user":
            formatted_messages.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            formatted_messages.append(AIMessage(content=msg.get("content", "")))

    # 3. Append the newest query exactly once
    formatted_messages.append(HumanMessage(content=user_input))

    # 4. Stream the execution and apply a micro-delay for natural typing effect
    for chunk in llm.stream(formatted_messages):
        content = chunk.content if isinstance(chunk.content, str) else str(chunk.content or "")
        words = content.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.04)