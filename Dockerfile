# Use the official PyTorch CPU image for Python 3.12.
FROM pytorch/pytorch:2.3.1-cpu-py3.12

# The PyTorch images already run as a non-root user (`torchuser`), so we don't need to create one.
# They also set up a working directory at /workspace/
WORKDIR /workspace/

# Temporarily switch to the root user to install system packages.
USER root

# Install essential system dependencies.
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    build-essential \
    curl \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install pget to a system-wide location.
RUN curl -o /usr/local/bin/pget -L "https://github.com/replicate/pget/releases/latest/download/pget_$(uname -s)_$(uname -m)" && \
    chmod +x /usr/local/bin/pget

# Copy your project files into the image and set correct ownership.
COPY --chown=torchuser:torchuser . .

# Switch back to the non-root user for all subsequent operations.
USER torchuser

# Install the remaining Python requirements.
# This will be much faster because torch, torchvision, etc., are already in the base image.
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install all custom nodes.
RUN python scripts/install_custom_nodes.py

# Copy the entrypoint script and make it executable.
COPY --chown=torchuser:torchuser scripts/run.sh .
RUN chmod +x run.sh

# This is the command that will run when the container starts.
ENTRYPOINT ["./run.sh"]