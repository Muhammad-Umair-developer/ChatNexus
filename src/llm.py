"""
llm.py

Handles all interactions with the LLM provider via LangChain.
Constructs prompt payloads, manages the model instance, and handles token streaming.
"""

import time
from typing import Generator
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
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
        model=LLM_MODEL
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
    
    # 2. Append historical context so the model "remembers" the conversation
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            formatted_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            formatted_messages.append(AIMessage(content=msg["content"]))
            
    # 3. Append the newest query
    formatted_messages.append(HumanMessage(content=user_input))
    
    # 4. Stream the execution and apply a micro-delay for UX purposes.
    # Gemini is often too fast for the frontend to render the "typing" effect naturally,
    # so we manually yield words with a 60ms delay.
    for chunk in llm.stream(formatted_messages):
        words = chunk.content.split(" ")
        for i, word in enumerate(words):
            # Reattach the trailing space unless it's the final word in the chunk
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.06)