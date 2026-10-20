import streamlit as st
from src.config import APP_NAME, logger
from src.ui_components import setup_page, render_chat_history
from src.llm import stream_response

# 1. Page Configuration
setup_page()

# 2. Render Existing Chat Messages
render_chat_history()

# 3. Chat Input and Event Loop
if prompt := st.chat_input(f"Message {APP_NAME}..."):
    
    # Log the interaction silently
    logger.info(f"Query received: {prompt[:50]}...")
    
    # Append and render user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Stream and render assistant response
    with st.chat_message("assistant"):
        try:
            # write_stream automatically creates the typewriter effect from the generator
            response_text = st.write_stream(stream_response(prompt))
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            logger.info("Response successfully streamed.")
        except Exception as e:
            logger.error(f"Nexus Core Error: {e}")
            st.error("Connection to ChatNexus core was interrupted. Please try again.")