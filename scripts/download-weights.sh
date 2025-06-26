#!/bin/bash
set -e

echo "--- Pre-warming model caches ---"

# Create target directories
mkdir -p /app/ComfyUI/models/BiRefNet
mkdir -p /root/.cache/torch/hub/checkpoints/

# Download BiRefNet Models
echo "Downloading BiRefNet models..."
pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/swin_large_patch4_window12_384_22kto1k.pth.tar" /app/ComfyUI/models/BiRefNet/
pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/pvt_v2_b2.pth.tar" /app/ComfyUI/models/BiRefNet/
pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/BiRefNet-ep480.pth.tar" /app/ComfyUI/models/BiRefNet/
pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/BiRefNet-DIS_ep580.pth.tar" /app/ComfyUI/models/BiRefNet/
pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/swin_base_patch4_window12_384_22kto1k.pth.tar" /app/ComfyUI/models/BiRefNet/
pget -xf "https://weights.replicate.delivery/default/comfy-ui/BiRefNet/pvt_v2_b5.pth.tar" /app/ComfyUI/models/BiRefNet/

# Download ControlNet Aux Model
echo "Downloading ControlNet Aux models..."
pget -xf "https://weights.replicate.delivery/default/comfy-ui/custom_nodes/comfyui_controlnet_aux/mobilenet_v2-b0353104.pth.tar" /root/.cache/torch/hub/checkpoints/

echo "--- Finished pre-warming caches ---"