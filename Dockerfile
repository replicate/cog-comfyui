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
    awscli \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory.
WORKDIR /app

# --- CACHING OPTIMIZATION ---

# 1. Install pget utility first, as it's needed for weight downloads.
RUN curl -o /usr/local/bin/pget -L "https://github.com/replicate/pget/releases/latest/download/pget_$(uname -s)_$(uname -m)" && \
    chmod +x /usr/local/bin/pget

# 2. Copy ONLY the requirements file and the new download script.
COPY requirements.txt .
COPY scripts/download-weights.sh scripts/

# 3. Install Python dependencies. This layer will be cached.
RUN pip install --no-cache-dir -r requirements.txt

# 4. Run the weight download script. This creates a large, separate, cacheable layer.
#    This layer will only be re-run if download-weights.sh changes.
RUN chmod +x scripts/download-weights.sh && ./scripts/download-weights.sh

# 5. Now copy the rest of your application code. Changes here won't trigger re-downloads.
COPY . .

# 6. Pre-install all custom nodes..
RUN python scripts/install_custom_nodes.py

# 7. Make the entrypoint script executable
RUN chmod +x scripts/run.sh

# 8. Define the entrypoint for the container.
ENTRYPOINT ["./scripts/run.sh"]