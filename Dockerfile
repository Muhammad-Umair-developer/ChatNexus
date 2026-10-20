# 1. Base Image: Use a slim, official Python image to keep the container small and fast
FROM python:3.12-slim

# 2. System Setup: Install curl for the healthcheck, then clean up to reduce image size
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 3. Working Directory: Set the internal execution path
WORKDIR /app

# 4. Dependency Caching: Copy ONLY requirements first. 
# This tells Docker to cache the installed packages so rebuilding is instant if your code changes but dependencies don't.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. App Code: Copy the rest of the application (respecting .dockerignore)
COPY . .

# 6. Security: Create a non-root user and grant it ownership of the /app directory
RUN useradd -m nexususer
RUN chown -R nexususer:nexususer /app
USER nexususer

# 7. Network: Expose Streamlit's default port
EXPOSE 8501

# 8. MLOps Reliability: Tell the orchestration system (like Kubernetes) how to check if the app crashed
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 9. Execution: The command that runs when the container starts
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]