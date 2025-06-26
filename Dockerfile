# Use the standard slim Python image, which is multi-architecture.
FROM python:3.12-slim

# Set environment variables.
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies as root.
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    build-essential \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory.
WORKDIR /app

# --- Caching Optimization ---
# 1. Copy only the requirements file.
COPY requirements.txt .

# 2. Install Python packages system-wide as root. This layer will be cached.
RUN pip install --no-cache-dir -r requirements.txt

# 3. Now copy the rest of your application code, including the populated ComfyUI submodule.
COPY . .

# Install pget utility to a system-wide location.
RUN curl -o /usr/local/bin/pget -L "https://github.com/replicate/pget/releases/latest/download/pget_$(uname -s)_$(uname -m)" && \
    chmod +x /usr/local/bin/pget

# Pre-install all custom nodes.
RUN python scripts/install_custom_nodes.py

# Make the entrypoint script executable.
# Note: We are using the simplified run.sh that calls predict.py directly.
RUN chmod +x scripts/run.sh

# Define the entrypoint for the container. All commands will run as root.
ENTRYPOINT ["./scripts/run.sh"]