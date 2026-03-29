# Multi-stage build for Cloud Run
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY job_agent/ ./job_agent/
COPY mcp_job_server/ ./mcp_job_server/
COPY main.py .

# Create non-root user for security
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Set environment for Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cloud Run expects port 8080
EXPOSE 8080

# Run the Flask app
CMD ["python", "main.py"]
