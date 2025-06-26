# Use the standard slim Python image, which is multi-architecture.
FROM python:3.12-slim

# Set environment variables.
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies.
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    build-essential \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Create and switch to a non-root user.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
WORKDIR $HOME/app

# Set the PATH to include user's local bin.
ENV PATH="$HOME/.local/bin:$PATH"

# --- Caching Optimization ---
# 1. Copy only the requirements file first.
COPY --chown=user:user requirements.txt .

# 2. Install Python dependencies. This layer will be cached.
RUN pip install --no-cache-dir --user -r requirements.txt

# 3. Now copy the rest of your application, including the populated ComfyUI submodule directory.
COPY --chown=user:user . .


# Install pget utility.
RUN curl -o /tmp/pget -L "https://github.com/replicate/pget/releases/latest/download/pget_$(uname -s)_$(uname -m)" && \
    install /tmp/pget $HOME/.local/bin/ && \
    rm /tmp/pget

# Pre-install all custom nodes.
RUN python scripts/install_custom_nodes.py

# Make the entrypoint script executable.
RUN chmod +x scripts/run.sh

# Define the entrypoint for the container.
ENTRYPOINT ["./scripts/run.sh"]