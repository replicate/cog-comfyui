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

# Create a non-root user.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
WORKDIR $HOME/app

# Set the PATH before pip install.
ENV PATH="$HOME/.local/bin:$PATH"

# Copy ONLY requirements.txt to leverage caching.
COPY --chown=user:user requirements.txt .

# Install Python dependencies.
RUN pip install --no-cache-dir --user -r requirements.txt

# Now copy the rest of your application code.
COPY --chown=user:user . .

# --- THIS IS THE CRUCIAL FIX ---
# Initialize and update the Git submodules (like ComfyUI) inside the container.
RUN git submodule update --init --recursive

# Install pget utility.
RUN curl -o /tmp/pget -L "https://github.com/replicate/pget/releases/latest/download/pget_$(uname -s)_$(uname -m)" && \
    install /tmp/pget $HOME/.local/bin/ && \
    rm /tmp/pget

# Pre-install all custom nodes.
RUN python scripts/install_custom_nodes.py

# Make entrypoint script executable.
RUN chmod +x scripts/run.sh

# Define the entrypoint for the container.
ENTRYPOINT ["./scripts/run.sh"]