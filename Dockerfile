# Use the standard slim Python image, which is multi-architecture (supports amd64 and arm64).
FROM python:3.12-slim

# Set environment variables to avoid interactive prompts during build.
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies, including build tools and curl.
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    build-essential \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user for better security.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
WORKDIR $HOME/app

# --- FIX: Set the PATH *before* running pip install ---
# This ensures that any scripts installed by pip are immediately available.
ENV PATH="$HOME/.local/bin:$PATH"

# Copy all your project files into the image.
COPY --chown=user:user . .

# Install Python requirements. This will be the longest step.
# The warnings you saw should now be gone.
RUN pip install --no-cache-dir --user -r requirements.txt

# Install pget utility to the user's local bin directory.
RUN curl -o /tmp/pget -L "https://github.com/replicate/pget/releases/latest/download/pget_$(uname -s)_$(uname -m)" && \
    install /tmp/pget $HOME/.local/bin/ && \
    rm /tmp/pget

# Pre-install all custom nodes.
RUN python scripts/install_custom_nodes.py

# Copy the entrypoint script and make it executable.
COPY --chown=user:user scripts/run.sh .
RUN chmod +x run.sh

# Define the entrypoint for the container.
ENTRYPOINT ["./run.sh"]