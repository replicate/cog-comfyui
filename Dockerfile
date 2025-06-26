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

# --- INSTALL UTILITIES FIRST ---
# 3. Install pget utility to a system-wide location so it can be used in subsequent steps.
RUN curl -o /usr/local/bin/pget -L "https://github.com/replicate/pget/releases/latest/download/pget_$(uname -s)_$(uname -m)" && \
    chmod +x /usr/local/bin/pget

# --- NOW COPY APP CODE AND PRE-WARM CACHES ---
# 4. Copy the rest of your application code.
COPY . .

# 5. Pre-warm the cache for custom node helper scripts.
RUN mkdir -p /app/ComfyUI/models/BiRefNet && \
    pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/swin_large_patch4_window12_384_22kto1k.pth.tar" /app/ComfyUI/models/BiRefNet/ && \
    pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/pvt_v2_b2.pth.tar" /app/ComfyUI/models/BiRefNet/ && \
    pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/BiRefNet-ep480.pth.tar" /app/ComfyUI/models/BiRefNet/ && \
    pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/BiRefNet-DIS_ep580.pth.tar" /app/ComfyUI/models/BiRefNet/ && \
    pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/swin_base_patch4_window12_384_22kto1k.pth.tar" /app/ComfyUI/models/BiRefNet/ && \
    pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/pvt_v2_b5.pth.tar" /app/ComfyUI/models/BiRefNet/

RUN mkdir -p /root/.cache/torch/hub/checkpoints/ && \
    pget -xf "https://weights.replicate.delivery/default/comfy-ui/custom_nodes/comfyui_controlnet_aux/mobilenet_v2-b0353104.pth.tar" /root/.cache/torch/hub/checkpoints/

# 6. Pre-install all custom nodes.
RUN python scripts/install_custom_nodes.py

# 7. Make the entrypoint script executable.
RUN chmod +x scripts/run.sh

# 8. Define the entrypoint for the container. All commands will run as root.
ENTRYPOINT ["./scripts/run.sh"]