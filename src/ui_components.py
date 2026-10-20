import streamlit as st
from src.config import APP_NAME, APP_ICON

def setup_page():
    """Configures page title, icon, and header layout."""
    st.set_page_config(page_title=APP_NAME, page_icon=APP_ICON, layout="centered")
    st.title(f"{APP_ICON} {APP_NAME}")
    st.caption("Netsol Internal AI Assistant")

def render_chat_history():
    """Displays stored chat messages from Streamlit session state."""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": f"Welcome to {APP_NAME}. How can I assist with your engineering workflow today?"}
        ]
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])