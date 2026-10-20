"""
app.py

The main orchestrator for ChatNexus. 
This script binds the frontend components to the backend LLM engine.
Run via: `streamlit run app.py`
"""

import streamlit as st
from src.config import APP_NAME, logger
from src.ui_components import setup_page, render_chat_history
from src.llm import stream_response

def main():
    """Main application loop executed by Streamlit."""
    
    # 1. Initialize UI and layout
    setup_page()

    # 2. Paint historical conversation state
    render_chat_history()

    # 3. Await user input
    # The walrus operator (:=) assigns the input and evaluates if it is non-empty simultaneously.
    if prompt := st.chat_input(f"Message {APP_NAME}..."):
        
        # Log the incoming query (truncated for privacy in logs)
        logger.info(f"Query received: {prompt[:50]}...")
        
        # Commit user message to state and render it
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # Execute LLM call and stream response to UI
        with st.chat_message("assistant"):
            try:
                # st.write_stream consumes the generator from llm.py and handles the visual update
                response_text = st.write_stream(stream_response(prompt))
                
                # Commit the final assembled response to state memory
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                logger.info("Response successfully streamed and committed to memory.")
                
            except Exception as e:
                # Catch broad exceptions to prevent the UI from crashing, and log the traceback internally
                logger.error(f"Nexus Core execution failed: {str(e)}", exc_info=True)
                st.error("Connection to ChatNexus core was interrupted. Please check internal logs.")

# Standard Python idiom to ensure the script is being executed directly, not imported
if __name__ == "__main__":
    main()