FROM python:3.12-slim

# Create non-root user
RUN useradd -m -r nexususer

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy code and set permissions
COPY . .
RUN chown -R nexususer:nexususer /app

USER nexususer

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]