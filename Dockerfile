# Dockerfile for ARM/Apple Silicon compatibility (slower build)
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    build-essential \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
WORKDIR $HOME/app

COPY --chown=user:user . .

RUN pip install --no-cache-dir --user -r requirements.txt

ENV PATH="$HOME/.local/bin:$PATH"


# Install pget - a useful utility.
# We use sudo because the base image might not give write permissions to /usr/local/bin for torchuser.
# A cleaner way is to install it to the user's local bin directory.
RUN curl -o /tmp/pget -L "https://github.com/replicate/pget/releases/latest/download/pget_$(uname -s)_$(uname -m)" && \
    mkdir -p /home/torchuser/.local/bin && \
    install /tmp/pget /home/torchuser/.local/bin/ && \
    rm /tmp/pget

# Pre-install all custom nodes.
RUN python scripts/install_custom_nodes.py

# Copy the entrypoint script and make it executable.
COPY --chown=torchuser:torchuser scripts/run.sh .
RUN chmod +x run.sh

# This is the command that will run when the container starts.
ENTRYPOINT ["./run.sh"]