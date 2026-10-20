# ⚡ ChatNexus

**An enterprise-grade, containerized AI engineering assistant MVP.**

ChatNexus is a modular, Streamlit-based AI chatbot designed for internal engineering workflows. Powered by Google's Gemini 2.5 Flash model and orchestrated via LangChain, it features a responsive Tailwind CSS hybrid UI, token-by-token text streaming, robust MLOps practices, and asynchronous logging.

## 🚀 Key Features

*   **High-Performance LLM Integration:** Utilizes `gemini-2.5-flash` via LangChain for rapid, context-aware technical assistance.
*   **Hybrid Responsive UI:** Combines Streamlit's native backend with injected Tailwind CSS for modern, right-aligned user messaging bubbles and custom system status dashboards.
*   **Token Streaming:** Implements a Python generator pipeline for real-time, ChatGPT-style typewriter text streaming.
*   **Enterprise Reliability:** Includes a comprehensive `pytest` suite for configuration safety and model initialization validation.
*   **MLOps Ready:** Fully containerized with a secure, non-root user `Dockerfile` and automated health checks.

---

## 🛠️ Technology Stack

*   **Frontend:** Streamlit, Tailwind CSS (via CDN), HTML5
*   **Backend & LLM:** Python 3.12, LangChain, Google GenAI
*   **Testing:** Pytest, Pytest-Mock
*   **Deployment:** Docker, Streamlit Community Cloud

---

## 💻 Local Development Setup

### Prerequisites
*   Python 3.11+
*   Google Gemini API Key

### 1. Clone & Environment Setup
```bash
git clone <your-repository-url>
cd ChatNexus
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory and add your Google API key:
```env
GOOGLE_API_KEY="your_api_key_here"
```

### 3. Run the Application
```bash
streamlit run app.py
```
The application will be available at `http://localhost:8501`.

---

## 🧪 Testing

This project maintains a robust test suite to validate configuration integrity and model behavior. To run the tests locally:

```bash
pytest -v
```

---

## 🐳 Docker Deployment

ChatNexus is fully containerized for scalable, secure deployment across any cloud environment.

### Build the Image
```bash
docker build -t chatnexus:v1 .
```

### Run the Container
*Note: The `--env-file` flag securely injects your local `.env` variables without baking them into the image.*
```bash
docker run -p 8501:8501 --env-file .env chatnexus:v1
```
Access the containerized application at `http://localhost:8501`.

---

## 📁 Project Structure

```text
ChatNexus/
├── .streamlit/
│   └── config.toml          # Global application theme settings
├── src/
│   ├── __init__.py
│   ├── config.py            # Environment validation & logging setup
│   ├── llm.py               # LangChain orchestration & streaming generator
│   └── ui_components.py     # Tailwind CSS injection & layout logic
├── tests/
│   ├── __init__.py
│   ├── test_config.py       # Security and constant validation
│   └── test_llm.py          # Model initialization tests
├── .dockerignore
├── .env                     # Local secrets (Not committed)
├── .gitignore
├── app.py                   # Main application entry point
├── Dockerfile               # Non-root container definition
└── requirements.txt         # Pinned dependencies
```