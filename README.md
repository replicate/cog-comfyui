# cog-comfyui

Run ComfyUI workflows on Replicate:

- https://replicate.com/comfyui/any-comfyui-workflow
- https://replicate.com/comfyui/any-comfyui-workflow-a100

We recommend:

- trying it on the website with your favorite workflow and making sure it works
- using your own instance to run your workflow quickly and efficiently on Replicate (see the guide below)
- using the production ready Replicate API to integrate your workflow into your own app or website

## What’s included

We've tried to include many of the most popular model weights and custom nodes:

- [View list of supported weights](https://github.com/replicate/cog-comfyui/blob/main/supported_weights.md)
- [View list of supported custom nodes](https://github.com/replicate/cog-comfyui/blob/main/custom_nodes.json)

Raise an issue to request more custom nodes or models, or use the `train` tab on Replicate to use your own weights (see below).

## How to use

### 1. Get your API JSON

You’ll need the API version of your ComfyUI workflow. This is different to the commonly shared JSON version, it does not included visual information about nodes, etc.

To get your API JSON:

1. Turn on the "Enable Dev mode Options" from the ComfyUI settings (via the settings icon)
2. Load your workflow into ComfyUI
3. Export your API JSON using the "Save (API format)" button

https://private-user-images.githubusercontent.com/319055/298630636-e3af1b59-ddd8-426c-a833-808e7f199fac.mp4

### 2. Gather your input files

If your model takes inputs, like images for img2img or controlnet, you have 3 options:

#### Use a URL

Modify your API JSON file to point at a URL:

```diff
- "image": "/your-path-to/image.jpg",
+ "image": "https://example.com/image.jpg",
```

#### Upload a single input

You can also upload a single input file when running the model.

This file will be saved as `input.[extension]` – for example `input.jpg`. It'll be placed in the ComfyUI `input` directory, so you can reference in your workflow with:

```diff
- "image": "/your-path-to/image.jpg",
+ "image": "image.jpg",
```

#### Upload a zip file or tar file of your inputs

These will be downloaded and extracted to the `input` directory. You can then reference them in your workflow based on their relative paths.

So a zip file containing:

```
- my_img.png
- references/my_reference_01.jpg
- references/my_reference_02.jpg
```

Might be used in the workflow like:

```
"image": "my_img.png",
...
"directory": "references",
```

### 3. Using custom LoRAs from CivitAI or HuggingFace

You can use LoRAs directly from CivitAI, HuggingFace, or any other URL in two ways:

#### Option 1: Use the LoraLoader node with a URL

Use the direct download URL as the `lora_name`:

```
{
    "inputs": {
      "lora_name": "https://huggingface.co/username/model/resolve/main/lora.safetensors",
      ...
    },
    "class_type": "LoraLoader"
}
```

#### Option 2: Use the LoraLoaderFromURL node

Alternatively, use the dedicated LoraLoaderFromURL node from [ComfyUI-GlifNodes](https://github.com/glifxyz/ComfyUI-GlifNodes):

```
{
    "inputs": {
      "url": "https://civitai.com/api/download/models/1163532",
      // ...
    },
    "class_type": "LoraLoaderFromURL"
}
```

Both methods work the same way - the standard LoraLoader will automatically switch to use LoraLoaderFromURL when it detects a URL in the `lora_name` field.

### Run your workflow

With all your inputs updated, you can now run your workflow.

Example:

```sh
# Pass in the workflow JSON as a string
cog predict -i workflow_json="{ ... }"

# Pass in the workflow JSON as a URL
cog predict -i workflow_json="https://example.com/your_workflow.json"

# Pass in the workflow JSON as a file
cog predict -i workflow_json=@your_workflow.json
```

Some workflows save temporary files, for example pre-processed controlnet images. You can also return these by enabling the `return_temp_files` option.

## How to use your own dedicated instance

The `any-comfyui-workflow` model on Replicate is a shared public model. This means many users will be sending workflows to it that might be quite different to yours. The effect of this will be that the internal ComfyUI server may need to swap models in and out of memory, this can slow down your prediction time.

ComfyUI and it's custom nodes are also continually being updated. While this means the newest versions are usually running, if there are breaking changes to custom nodes then your workflow may stop working.

If you have your own dedicated instance you will:

- fix the code and custom nodes to a known working version
- have a faster prediction time by keeping just your models in memory
- benefit from ComfyUI’s own internal optimisations when running the same workflow repeatedly

### Options for using your own instance

To get the best performance from the model you should run a dedicated instance. You have 3 choices:

1. Create a private deployment (simplest, but you'll need to pay for setup and idle time)
2. Create and deploy a fork using Cog (most powerful but most complex)
3. Create a new model from the train tab (simple, your model can be public or private and you can bring your own weights)

### 1. Create a private deployment

Go to:

https://replicate.com/deployments/create

Select `comfyui/any-comfyui-workflow` as the model you'd like to deploy. Pick your hardware and min and max instances, and you're ready to go. You'll be pinned to the version you deploy from. When `any-comfyui-workflow` is updated, you can test your workflow with it, and then deploy again using the new version.

You can read more about deployments in the Replicate docs:

https://replicate.com/docs/deployments

### 2. Create and deploy a fork using Cog

You can use this repository as a template to create your own model. This gives you complete control over the ComfyUI version, custom nodes, and the API you'll use to run the model.

You'll need to be familiar with Python, and you'll also need a GPU to push your model using [Cog](https://cog.run). Replicate has a good getting started guide: https://replicate.com/docs/guides/push-a-model

#### Example

The `kolors` model on Replicate is a good example to follow:

- https://replicate.com/fofr/kolors (The model with it’s customised API)
- https://github.com/replicate/cog-comfyui-kolors (The new repo)

It was created from this repo, and then deployed using Cog. You can step through the commits of that repo to see what was changed and how, but broadly:

- this repository is used as a template
- the script [`scripts/prepare_template.py`](https://github.com/replicate/cog-comfyui/blob/main/scripts/prepare_template.py) is run first, to remove examples and unnecessary boilerplate
- `custom_nodes.json` is modified to add or remove custom nodes you need, making sure to also add or remove their dependencies from `cog.yaml`
- run `./scripts/install_custom_nodes.py` to install the custom nodes (or `./scripts/reset.py` to reinstall ComfyUI and all custom nodes)
- the workflow is added as `workflow_api.json`
- `predict.py` is updated with a new API and the `update_workflow` method is changed so that it modifies the right parts of the JSON
- the model is tested using `cog predict -i option_name=option_value -i another_option_name=another_option_value` on a GPU
- the model is pushed to Replicate using `cog push r8.im/your-username/your-model-name`

### 3. Create a new model from the train tab

Visit the train tab on Replicate:

https://replicate.com/comfyui/any-comfyui-workflow/train

Here you can give public or private URLs to weights on HuggingFace and CivitAI. If URLs are private or need authentication, make sure to include an API key or access token.

Check the training logs to see what filenames to use in your workflow JSON. For example:

```
Downloading from HuggingFace:
...
Size of the tar file: 217.88 MB
====================================
When using your new model, use these filenames in your JSON workflow:
araminta_k_midsommar_cartoon.safetensors
```

After running the training, you'll have your own ComfyUI model with your customised weights loaded during model setup. To prevent others from using it, you can make it private. Private models are billed differently to public models on Replicate.

## Developing locally

Clone this repository:

```sh
git clone --recurse-submodules https://github.com/replicate/cog-comfyui.git
```

Run the [following script](https://github.com/replicate/cog-comfyui/blob/main/scripts/install_custom_nodes.py) to install all the custom nodes:

```sh
./scripts/install_custom_nodes.py
```

You can view the list of nodes in [custom_nodes.json](https://github.com/replicate/cog-comfyui/blob/main/custom_nodes.json)

### Running the Web UI from your Cog container

1. **GPU Machine**: Start the Cog container and expose port 8188:
```sh
sudo cog run -p 8188 bash
```
Running this command starts up the Cog container and let's you access it

2. **Inside Cog Container**: Now that we have access to the Cog container, we start the server, binding to all network interfaces:
```sh
cd ComfyUI/
python main.py --listen 0.0.0.0
```

3. **Local Machine**: Access the server using the GPU machine's IP and the exposed port (8188):
`http://<gpu-machines-ip>:8188`

When you goto `http://<gpu-machines-ip>:8188` you'll see the classic ComfyUI web form!
