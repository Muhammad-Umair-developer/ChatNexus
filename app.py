"""
app.py

The main orchestrator for ChatNexus. 
Run via: `streamlit run app.py`
"""

import streamlit as st
from src.config import APP_NAME, APP_ICON, logger
from src.ui_components import setup_page, render_chat_history, render_user_message
from src.llm import stream_response

def main():
    setup_page()
    render_chat_history()

    if prompt := st.chat_input(f"Message {APP_NAME}..."):
        
        logger.info(f"Query received: {prompt[:50]}...")
        
        # Commit user message to state
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Inject the custom right-aligned Tailwind UI
        render_user_message(prompt)
            
        # Keep the assistant left-aligned to allow token streaming
        with st.chat_message("assistant", avatar=APP_ICON):
            try:
                response_text = st.write_stream(stream_response(prompt))
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                logger.info("Response successfully streamed and committed.")
            except Exception as e:
                logger.error(f"Nexus Core execution failed: {str(e)}", exc_info=True)
                st.error("Connection to ChatNexus core was interrupted. Please check internal logs.")

if __name__ == "__main__":
    main()