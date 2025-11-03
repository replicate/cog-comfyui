#!/usr/bin/env python
import argparse
import subprocess
import os
import sys
import json
import requests
import urllib.parse
import time
from datetime import datetime


def check_gcloud_auth():
    try:
        result = subprocess.run(
            ["gcloud", "auth", "list"], capture_output=True, text=True
        )
        if "No credentialed accounts." in result.stdout:
            print(
                "Error: Not authenticated with gcloud. Please run 'gcloud auth login' first."
            )
            sys.exit(1)
    except subprocess.CalledProcessError:
        print("Error: Failed to check gcloud authentication status.")
        sys.exit(1)


def is_civitai_url(url: str):
    return url.startswith("https://civitai.com")


def civitai_url_with_token(url: str, civitai_api_token: str):
    if not is_civitai_url(url):
        return url

    if not civitai_api_token:
        return url

    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    query_params["token"] = [civitai_api_token]
    new_query = urllib.parse.urlencode(query_params, doseq=True)
    return urllib.parse.urlunparse(parsed_url._replace(query=new_query))


def is_huggingface_url(url: str):
    return url.startswith("https://huggingface.co")


def extract_parts_from_huggingface_url(url: str):
    # HUGGINGFACE_CO_URL_TEMPLATE
    # https://huggingface.co/{repo_id}/resolve/{revision}/{filename}

    parsed_url = urllib.parse.urlparse(url)
    path_parts = parsed_url.path.split("/")

    if len(path_parts) < 5:
        raise ValueError(
            f"HuggingFace URL does not contain enough parts to extract all required parts: {url}"
        )

    repo_id = f"{path_parts[1]}/{path_parts[2]}"
    revision = path_parts[4]
    filename_and_path = path_parts[5:]
    filename = filename_and_path[-1]

    return repo_id, revision, filename_and_path, filename


def get_filename_from_huggingface_url(url: str):
    parsed_url = urllib.parse.urlparse(url)
    path_parts = parsed_url.path.split("/")

    if len(path_parts) < 5:
        raise ValueError(
            f"HuggingFace URL does not contain enough parts to extract filename: {url}"
        )

    filename = path_parts[-1]
    return filename


def get_filename_from_content_disposition(content_disposition):
    filename = None
    if "filename*" in content_disposition:
        filename_star = content_disposition.split("filename*=")[1].split(";")[0].strip()
        filename = urllib.parse.unquote(filename_star.split("''")[1])
    elif "filename" in content_disposition:
        filename = content_disposition.split("filename=")[1].split(";")[0].strip('"')

    return filename


def get_filename_from_url(url, civitai_api_token: str = None):
    if is_civitai_url(url):
        url = civitai_url_with_token(url, civitai_api_token)

    try:
        response = requests.head(url, allow_redirects=True)

        if "Content-Disposition" in response.headers:
            content_disposition = response.headers["Content-Disposition"]
            filename = get_filename_from_content_disposition(content_disposition)
        else:
            response = requests.get(
                url,
                headers={"Range": "bytes=0-1024"},
                stream=True,
                allow_redirects=True,
            )
            if "Content-Disposition" in response.headers:
                content_disposition = response.headers["Content-Disposition"]
                filename = get_filename_from_content_disposition(content_disposition)
            else:
                filename = url.split("/")[-1]

        if "." not in filename:
            print(f"No extension found for {filename}, assuming safetensors")
            filename += ".safetensors"

        return filename
    except Exception as e:
        print(f"Error: Failed to get filename from {url}: {e}")
        return None


def download_file(url, filename=None, civitai_api_token=None, hf_cli_download=False):
    start_time = time.time()
    huggingface_read_token = os.environ.get("HUGGINGFACE_READ_TOKEN")
    if is_civitai_url(url):
        if not filename:
            filename = get_filename_from_url(url, civitai_api_token)
            filename = confirm_filename(filename)
        url = civitai_url_with_token(url, civitai_api_token)
        print(f"Downloading {url} to {filename}")
        try:
            result = subprocess.run(["pget", "-f", url, filename], timeout=600)
            if result.returncode != 0:
                raise RuntimeError(
                    "Download failed. You may need to pass in a valid CivitAI API token."
                )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Download failed due to timeout")
    elif is_huggingface_url(url):
        if hf_cli_download:
            repo_id, revision, filename_and_path, extracted_filename = (
                extract_parts_from_huggingface_url(url)
            )
            if not filename:
                filename = extracted_filename
                filename = confirm_filename(filename)
            print(f"Downloading from HuggingFace Hub: {url} to {filename}")

            token = huggingface_read_token if huggingface_read_token else None
            subprocess.run(
                [
                    "hf",
                    "download",
                    repo_id,
                    "/".join(filename_and_path),
                    "--revision",
                    revision,
                    "--local-dir",
                    os.getcwd(),
                    "--local-dir-use-symlinks",
                    "False",
                    "--force-download",
                    *(["--token", token] if token else []),
                ]
            )
        else:
            if not filename:
                filename = get_filename_from_huggingface_url(url)
                filename = confirm_filename(filename)
            print(f"Downloading from HuggingFace: {url} to {filename}")
            subprocess.run(["pget", "-f", url, filename])
    else:
        if not filename:
            filename = get_filename_from_url(url)
            filename = confirm_filename(filename)
        print(f"Downloading {url} to {filename}")
        subprocess.run(["pget", "-f", url, filename])

    print(f"Successfully downloaded {filename}")
    end_time = time.time()
    print(f"Downloaded in: {end_time - start_time:.2f} seconds")
    return filename


def tar_file(filename):
    if filename is None:
        raise ValueError("Filename cannot be None")
    tar_filename = filename + ".tar"
    subprocess.run(["tar", "-cvf", tar_filename, filename])
    print(f"Tarred {filename} to {tar_filename}")
    return tar_filename


def upload_to_gcloud(local_file, destination_blob_name, subfolder):
    destination_path = (
        f"{destination_blob_name}/{subfolder}/{local_file}"
        if subfolder
        else f"{destination_blob_name}/{local_file}"
    )
    print(f"Uploading {local_file} to {destination_path}")
    subprocess.run(["gcloud", "storage", "cp", local_file, destination_path])
    print(f"Uploaded to {destination_path}")


def upload_to_huggingface(local_file, subfolder):
    print(f"Uploading {local_file} to huggingface under {subfolder}")
    subprocess.run(
        [
            "hf",
            "upload",
            "fofr/comfyui",
            local_file,
            f"{subfolder}/{local_file}",
        ]
    )
    print(f"Uploaded {local_file} to huggingface under {subfolder}")


def remove_files(*filenames):
    for filename in filenames:
        os.remove(filename)
        print(f"Deleted {filename}")


def get_subfolder():
    subfolders = [
        "checkpoints",
        "upscale_models",
        "text_encoders",
        "clip_vision",
        "loras",
        "loras/b_lora",
        "embeddings",
        "controlnet",
        "ipadapter",
        "vae",
        "diffusion_models",
        "photomaker",
        "instantid",
        "insightface",
        "facedetection",
        "facerestore_models",
        "mmdets",
        "sams",
        "grounding-dino",
        "ultralytics",
        "inpaint",
        "birefnet",
        "animatediff_models",
        "animatediff_motion_lora",
        "custom_nodes/comfyui_controlnet_aux",
        "Other",
    ]
    for i, subfolder in enumerate(subfolders, start=1):
        print(f"{i}. {subfolder}")
    choice = int(
        input("Choose the type of file by selecting the corresponding number: ")
    )
    if choice == len(subfolders):
        return input("Enter the subfolder name: ")
    else:
        return subfolders[choice - 1]


def update_weights_json(subfolder, filename, url):
    subfolder = subfolder.upper()
    with open("weights.json", "r+") as f:
        weights_data = json.load(f)
        if "/" in subfolder and subfolder not in weights_data:
            main_folder, sub_path = subfolder.split("/", 1)
            sub_path = sub_path.lower()
            if main_folder in weights_data:
                subfolder = main_folder
                filename = f"{sub_path}/{filename}"
            else:
                print(f"{subfolder} not found in weights.json")
                return

        if subfolder in weights_data:
            if filename not in weights_data[subfolder]:
                weights_data[subfolder].append(filename)
                f.seek(0)
                json.dump(weights_data, f, indent=4)
                f.truncate()
                print(f"Added {filename} to {subfolder} in weights.json")
                update_changelog(subfolder, filename, url)
            else:
                print(f"{filename} already exists in {subfolder} in weights.json")
        else:
            print(f"{subfolder} not found in weights.json")


def update_changelog(subfolder, filename, url):
    changelog_file = "CHANGELOG.md"
    today = datetime.now().strftime("%Y-%m-%d")
    if url:
        # Convert HuggingFace download URLs to blob URLs
        if url.startswith("https://huggingface.co") and "/resolve/" in url:
            url = url.replace("/resolve/", "/blob/")
            if "?download=true" in url:
                url = url.replace("?download=true", "")
        update_line = f"- [{filename} ({subfolder.lower()})]({url})\n"
    else:
        update_line = f"- {filename} ({subfolder.lower()})\n"

    try:
        with open(changelog_file, "r+") as file:
            content = file.readlines()
            if content[0].strip() != f"## {today}":
                content.insert(0, f"\n## {today}\n\n")

            # Find the index of the current day's section
            today_index = next(
                (i for i, line in enumerate(content) if line.strip() == f"## {today}"),
                None,
            )

            if today_index is not None:
                # Insert the update line right after the current day's header
                content.insert(today_index + 1, update_line)
            else:
                # If today's section wasn't found (which shouldn't happen), append to the top
                content.insert(2, update_line)

            file.seek(0)
            file.writelines(content)
    except FileNotFoundError:
        print(
            f"Warning: Changelog file '{changelog_file}' not found. Skipping changelog update."
        )
    except IOError as e:
        print(f"Error updating changelog: {e}")


def confirm_filename(filename):
    while True:
        confirmed = input(f"Confirm filename {filename} (y/n): ").lower()
        if confirmed == "y":
            return filename
        elif confirmed == "n":
            new_filename = input("Enter new filename: ")
            return new_filename
        else:
            print("Invalid input. Please enter 'y' or 'n'.")


def process_file(
    url=None,
    filename=None,
    subfolder=None,
    no_hf_upload=False,
    civitai_api_token=None,
    hf_cli_download=False,
    no_upload=False,
):
    if url:
        print(f"Processing {url}")
        if no_upload and filename:
            local_file = filename
        else:
            local_file = download_file(url, filename, civitai_api_token, hf_cli_download)
    else:
        if filename is None:
            raise ValueError("Filename must be provided if URL is not specified")
        print(f"Processing {filename}")
        local_file = filename

    if not no_upload:
        tarred_file = tar_file(local_file)
        upload_to_gcloud(tarred_file, "gs://replicate-weights/comfy-ui", subfolder)
        if not no_hf_upload:
            upload_to_huggingface(local_file, subfolder)
        remove_files(local_file, tarred_file)

    update_weights_json(subfolder, local_file, url)
    subprocess.run(["python", "scripts/sort_weights.py"])


def process_weights_file(
    weights_file,
    subfolder=None,
    no_hf_upload=False,
    civitai_api_token=None,
    hf_cli_download=False,
    no_upload=False,
):
    with open(weights_file, "r") as f:
        for line in f:
            url, filename = line.strip().split()
            process_file(
                url,
                filename,
                subfolder,
                no_hf_upload,
                civitai_api_token,
                hf_cli_download,
                no_upload,
            )


def main():
    check_gcloud_auth()

    parser = argparse.ArgumentParser(
        description="Download a file, tar it, and upload to Google Cloud Storage and huggingface"
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="The URL of the file to download or the local file to process",
    )
    parser.add_argument(
        "filename",
        nargs="?",
        help="The local filename to save the file as. Defaults to the filename in the URL",
    )
    parser.add_argument(
        "--weights_list",
        help="The weights list file with URLs to download",
    )
    parser.add_argument(
        "--no_hf_upload",
        action="store_true",
        help="Do not upload to Hugging Face",
    )
    parser.add_argument(
        "--hf_cli_download",
        action="store_true",
        help="Use Hugging Face Hub to download weights",
    )
    parser.add_argument(
        "--no_upload",
        action="store_true",
        help="Skip uploading to storage but still update changelog and weights.json",
    )
    args = parser.parse_args()

    subfolder = get_subfolder()
    civitai_api_token = os.environ.get("CIVITAI_API_TOKEN")

    if args.weights_list:
        process_weights_file(
            args.weights_list,
            subfolder,
            args.no_hf_upload,
            civitai_api_token,
            args.hf_cli_download,
            args.no_upload,
        )
    elif args.file:
        filename = args.filename if args.filename else None
        if args.file.startswith(("http://", "https://")):
            process_file(
                url=args.file,
                filename=filename,
                subfolder=subfolder,
                no_hf_upload=args.no_hf_upload,
                civitai_api_token=civitai_api_token,
                hf_cli_download=args.hf_cli_download,
                no_upload=args.no_upload,
            )
        elif os.path.isfile(args.file):
            process_file(
                filename=args.file,
                subfolder=subfolder,
                no_hf_upload=args.no_hf_upload,
                civitai_api_token=civitai_api_token,
                hf_cli_download=args.hf_cli_download,
                no_upload=args.no_upload,
            )
        else:
            print(f"Error: The file or URL {args.file} is not valid.")
            sys.exit(1)


if __name__ == "__main__":
    main()
