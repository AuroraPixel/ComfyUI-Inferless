#!/bin/bash
set -e

# Add python paths
export PATH="/usr/local/bin:$PATH"

# Try to use comfy command, if fails use python -m
if command -v comfy &> /dev/null; then
    COMFY_CMD="comfy"
else
    COMFY_CMD="python -m comfy_cli"
fi

echo "Using ComfyUI command: $COMFY_CMD"

# Use VOLUME_NFS instead of NFS_VOLUME to match the environment variable
WORKSPACE_PATH=${VOLUME_NFS:-${NFS_VOLUME:-/tmp}}

$COMFY_CMD --skip-prompt --workspace=$WORKSPACE_PATH/ComfyUI install --nvidia
$COMFY_CMD --skip-prompt model download --url https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors --relative-path models/unet --set-civitai-api-token $HF_ACCESS_TOKEN
$COMFY_CMD --skip-prompt model download --url https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors --relative-path models/clip
$COMFY_CMD --skip-prompt model download --url https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors --relative-path models/clip
$COMFY_CMD --skip-prompt model download --url https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors --relative-path models/clip
$COMFY_CMD --skip-prompt model download --url https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors --relative-path models/vae
$COMFY_CMD --skip-prompt model download --url https://huggingface.co/autismanon/modeldump/resolve/main/dreamshaper_8.safetensors --relative-path models/checkpoints
mkdir -p "$WORKSPACE_PATH/workflows"
