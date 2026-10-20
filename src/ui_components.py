"""
ui_components.py

Handles Streamlit UI rendering, Tailwind CSS injection, and responsive layouts.
"""

import html
import streamlit as st
from src.config import APP_NAME, APP_ICON, LLM_MODEL

def inject_tailwind() -> None:
    """Injects the Tailwind CSS CDN and hides default Streamlit chrome."""
    st.markdown(
        """
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 800px; }
        </style>
        """, 
        unsafe_allow_html=True
    )

def setup_page() -> None:
    """Bootstraps the main page layout, injects Tailwind, and builds the sidebar."""
    st.set_page_config(
        page_title=APP_NAME, 
        page_icon=APP_ICON, 
        layout="centered",
        initial_sidebar_state="expanded"
    )
    
    inject_tailwind()
    
    # --- Professional Sidebar ---
    with st.sidebar:
        st.title(f"{APP_ICON} {APP_NAME}")
        st.caption("Netsol Internal AI System")
        st.divider()
        
        status_html = f"""
        <div class="bg-slate-800 p-4 rounded-xl border border-slate-700 shadow-lg mb-6">
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">System Status</h3>
            <div class="space-y-3 text-sm">
                <div class="flex items-center justify-between">
                    <span class="text-slate-300">Core Engine</span>
                    <span class="flex items-center text-emerald-400 font-medium">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 mr-2 animate-pulse"></span>Online
                    </span>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-slate-300">Active Model</span>
                    <span class="text-blue-400 font-mono text-xs bg-blue-900/30 px-2 py-1 rounded">{LLM_MODEL}</span>
                </div>
            </div>
        </div>
        """
        st.markdown(status_html, unsafe_allow_html=True)
        
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = [
                {
                    "role": "assistant", 
                    "content": f"Session cleared. Welcome back to {APP_NAME}. How can I assist you?"
                }
            ]
            st.rerun()

    st.title(f"{APP_ICON} {APP_NAME}")
    st.caption("Your Versatile AI Engineering Assistant")

def render_user_message(content: str) -> None:
    """Renders the user's message as a right-aligned Tailwind chat bubble."""
    # Sanitize input for security and preserve line breaks
    safe_content = html.escape(content).replace("\n", "<br>")
    
    user_html = f"""
    <div class="flex justify-end mb-6 w-full">
        <div class="bg-blue-600 text-white px-5 py-3 rounded-2xl rounded-tr-sm max-w-[85%] shadow-md text-sm leading-relaxed">
            {safe_content}
        </div>
        <div class="ml-3 text-2xl mt-1 flex-shrink-0">👤</div>
    </div>
    """
    st.markdown(user_html, unsafe_allow_html=True)

def render_chat_history() -> None:
    """Renders all historical chat messages."""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": f"Welcome to {APP_NAME}. How can I assist with your engineering workflow today?"
            }
        ]
        
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            render_user_message(msg["content"])
        else:
            with st.chat_message("assistant", avatar=APP_ICON):
                st.markdown(msg["content"])