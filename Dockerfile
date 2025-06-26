# Use the standard slim Python image, which is multi-architecture (supports amd64 and arm64).
FROM python:3.12-slim

# Set environment variables.
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies. This layer is very stable and will be cached.
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    build-essential \
    curl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user. This layer will be cached.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user
WORKDIR $HOME/app

# Set the PATH. This layer will be cached.
ENV PATH="$HOME/.local/bin:$PATH"

# --- CACHING OPTIMIZATION ---
# First, copy ONLY the requirements file.
COPY --chown=user:user requirements.txt .

# Now, install the dependencies. This layer will now be cached as long as
# requirements.txt doesn't change. This is the key to speeding up your builds.
RUN pip install --no-cache-dir --user -r requirements.txt

# Now that the slow part is done and cached, copy the rest of your application code.
# Changes to your scripts or workflows will only invalidate the cache from this point onward.
COPY --chown=user:user . .

# Install pget utility to the user's local bin directory.
RUN curl -o /tmp/pget -L "https://github.com/replicate/pget/releases/latest/download/pget_$(uname -s)_$(uname -m)" && \
    install /tmp/pget $HOME/.local/bin/ && \
    rm /tmp/pget

# Pre-install all custom nodes. This will run if your custom node scripts change.
RUN python scripts/install_custom_nodes.py

# The entrypoint setup will also be cached unless run.sh changes.
RUN chmod +x scripts/run.sh
ENTRYPOINT ["./scripts/run.sh"]