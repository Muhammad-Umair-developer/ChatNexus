import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.config import LLM_MODEL, TEMPERATURE

SYSTEM_PROMPT = """You are ChatNexus, a highly capable internal AI assistant at Netsol. 
Your goal is to assist software engineers, data scientists, and team members with clear, concise, 
and accurate technical solutions, architectural guidance, and debugging help."""

def get_chat_model():
    """Instantiates the Google Gemini chat model."""
    return ChatGoogleGenerativeAI(temperature=TEMPERATURE, model=LLM_MODEL)

def generate_response(user_input: str) -> str:
    """Invokes the model with conversational context and returns the text response."""
    llm = get_chat_model()
    
    # Build conversation payload with system prompt
    formatted_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    
    # Append prior conversation history from session_state
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            formatted_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            formatted_messages.append(AIMessage(content=msg["content"]))
            
    # Add current prompt
    formatted_messages.append(HumanMessage(content=user_input))
    
    response = llm.invoke(formatted_messages)
    return response.content