import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# Initialize the model using the API key from your .env
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

def generate_ai_response(chat_history: list, new_message: str) -> str:
    """Reconstructs history and fetches the next AI response."""
    messages = [SystemMessage(content="You are ChatNexus, a professional AI assistant.")]
    
    # Append historical messages
    for msg in chat_history:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))
            
    # Append the new user message
    messages.append(HumanMessage(content=new_message))
    
    response = llm.invoke(messages)
    return response.content