"""
ui_components.py

Handles all Streamlit UI rendering and layout logic.
By isolating UI components, we ensure the core LLM logic remains framework-agnostic.
"""

import streamlit as st
from src.config import APP_NAME, APP_ICON

def setup_page() -> None:
    """
    Bootstraps the main Streamlit page layout and metadata.
    Must be the first Streamlit command executed in the app.
    """
    st.set_page_config(
        page_title=APP_NAME, 
        page_icon=APP_ICON, 
        layout="centered"
    )
    st.title(f"{APP_ICON} {APP_NAME}")
    st.caption("Your Versatile AI Assistant")

def render_chat_history() -> None:
    """
    Iterates through the session state and renders all historical chat messages.
    Streamlit re-runs the entire script on every user interaction, so we must 
    persist and re-render the conversation history from memory.
    """
    # Initialize the memory store on the very first page load
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": f"Welcome to {APP_NAME}. How can I assist with your engineering workflow today?"
            }
        ]
        
    # Paint the historical messages onto the UI
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])