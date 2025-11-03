from custom_node_helper import CustomNodeHelper


FLASHVSR_WEIGHTS = [
    "Wan2_1-T2V-1_3B_FlashVSR_fp32.safetensors",
    "Wan2.1_VAE.safetensors",
    "Wan2_1_FlashVSR_LQ_proj_model_bf16.safetensors",
    "Wan2_1_FlashVSR_TCDecoder_fp32.safetensors",
    "Prompt.safetensors",
]


class ComfyUI_FlashVSR(CustomNodeHelper):
    @staticmethod
    def add_weights(weights_to_download, node):
        if node.is_type_in([
            "AILab_FlashVSR",
            "AILab_FlashVSR_Advanced",
        ]):
            weights_to_download.extend(FLASHVSR_WEIGHTS)
