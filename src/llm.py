import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.config import LLM_MODEL, TEMPERATURE

# Professional Netsol Persona
SYSTEM_PROMPT = """You are ChatNexus, a proprietary AI engineering assistant developed internally for Netsol. 
You provide concise, highly technical, and accurate architectural guidance, code reviews, and debugging help.
Never reveal the underlying LLM architecture; maintain your identity strictly as a Netsol system."""

def get_chat_model():
    """Instantiates the chat model."""
    return ChatGoogleGenerativeAI(temperature=TEMPERATURE, model=LLM_MODEL)

def stream_response(user_input: str):
    """Yields the model response chunk-by-chunk for a streaming UI effect."""
    llm = get_chat_model()
    
    # Build conversation payload
    formatted_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    
    # Append prior conversation history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            formatted_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            formatted_messages.append(AIMessage(content=msg["content"]))
            
    # Add current prompt
    formatted_messages.append(HumanMessage(content=user_input))
    
    # Stream the response back
    for chunk in llm.stream(formatted_messages):
        yield chunk.content