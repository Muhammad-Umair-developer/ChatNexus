import streamlit as st
from src.config import APP_NAME
from src.ui_components import setup_page, render_chat_history
from src.llm import generate_response

# 1. Page Configuration
setup_page()

# 2. Render Existing Chat Messages
render_chat_history()

# 3. Chat Input and Event Loop
if prompt := st.chat_input(f"Message {APP_NAME}..."):
    # Append and render user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Generate and stream/render assistant response
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            try:
                response_text = generate_response(prompt)
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                st.error(f"Error connecting to ChatNexus core: {e}")