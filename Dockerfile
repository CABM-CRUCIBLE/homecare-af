FROM python:3.11-slim

# Install system dependencies (git, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition
COPY pyproject.toml .

# Install dependencies
RUN pip install --no-cache-dir -e .

# Copy source code and templates
COPY src/ src/
COPY templates/ templates/
COPY docs/ docs/

# Set environment defaults
ENV PYTHONUNBUFFERED=1
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT=7860

# Expose Gradio Web UI port
EXPOSE 7860

# Default entrypoint: launch Gradio Web UI
CMD ["homecare-agent", "web", "--host", "0.0.0.0", "--port", "7860"]
