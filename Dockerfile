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
# First, copy ONLY the requirements file.
COPY requirements.txt .

# Install Python packages system-wide as root.
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of your application code.
COPY . .

# Install pget utility to a system-wide location.
RUN curl -o /usr/local/bin/pget -L "https://github.com/replicate/pget/releases/latest/download/pget_$(uname -s)_$(uname -m)" && \
    chmod +x /usr/local/bin/pget

# Pre-install all custom nodes.
RUN python scripts/install_custom_nodes.py

# Make the entrypoint script executable.
RUN chmod +x scripts/run.sh

# Define the entrypoint for the container.
ENTRYPOINT ["./scripts/run.sh"]