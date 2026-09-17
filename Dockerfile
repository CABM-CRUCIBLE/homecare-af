FROM python:3.11-slim

# Install system dependencies (git, curl, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency definition and README required by hatchling metadata validation
COPY pyproject.toml README.md ./

# Copy source code, templates, and docs
COPY src/ src/
COPY templates/ templates/
COPY docs/ docs/

# Install framework and dependencies
RUN pip install --no-cache-dir -e .

# Set environment defaults
ENV PYTHONUNBUFFERED=1
ENV GRADIO_SERVER_NAME="0.0.0.0"
ENV GRADIO_SERVER_PORT=7860

# Expose Gradio Web UI port
EXPOSE 7860

# Default entrypoint: launch Gradio Web UI
CMD ["homecare-agent", "web", "--port", "7860"]
