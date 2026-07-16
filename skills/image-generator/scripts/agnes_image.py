#!/usr/bin/env python3
"""
Agnes AI Image Generation Script

Calls Agnes AI's image generation API to create images
from text prompts (text-to-image) or edit images (image-to-image).

Official docs: https://agnes-ai.com/doc/agnes-image-21-flash

Key API rules:
  - model, prompt, size are required for text-to-image
  - For image-to-image, put input image in extra_body.image (NOT top-level image)
  - response_format MUST go inside extra_body, NOT at top level
  - Use return_base64: true (top-level) for text-to-image base64 output
  - Use extra_body.response_format: "b64_json" for image-to-image base64 output

Usage:
  # Text-to-image (size is required)
  python agnes_image.py --prompt "a cat in space" --size "1024x768" --output cat.png

  # Image-to-image
  python agnes_image.py --prompt "make it cyberpunk" --image https://example.com/cat.png --size "1024x768" --output cyber_cat.png
"""

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

# Shared helpers from scripts/lib/utils.py (run as a script -> scripts/ is on
# sys.path[0]; the insert keeps it import-safe under other loaders too).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.utils import download_file, get_api_key, load_config  # noqa: E402

DEFAULT_BASE_URL = "https://apihub.agnes-ai.com/v1"
DEFAULT_IMAGE_MODEL = "agnes-image-2.1-flash"


def main():
    cfg = load_config()
    parser = argparse.ArgumentParser(
        description="Agnes AI Image Generation (text-to-image / image-to-image)"
    )
    parser.add_argument("--prompt", required=True, help="Text prompt for image generation or editing")
    parser.add_argument("--image", default=None,
                        help="Input image URL for image-to-image editing (also supports data:image/...;base64,...)")
    parser.add_argument("--size", required=True, help="Output size, e.g. 1024x768 (required)")
    parser.add_argument(
        "--model", default=cfg.get("default_image_model", DEFAULT_IMAGE_MODEL),
        help=f"Model name (default: {cfg.get('default_image_model', DEFAULT_IMAGE_MODEL)})"
    )
    parser.add_argument("--output", "-o", default=None, help="Output file path (default: auto-generated)")
    parser.add_argument("--api-key", default=None, help="API key (or set AGNES_API_KEY env var)")
    parser.add_argument("--base-url", default=cfg.get("base_url", DEFAULT_BASE_URL), help="API base URL")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output structured JSON result")
    parser.add_argument("--retries", type=int, default=3, help="Max retries for API call (default: 3)")

    args = parser.parse_args()
    api_key = get_api_key(args.api_key)

    # Build request payload
    # Per official docs: model, prompt, size are required for text-to-image
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
    }

    # For image-to-image: input image goes in extra_body.image (NOT top-level)
    # Per official docs examples and troubleshooting section
    extra_body = {}
    if args.image:
        extra_body["image"] = [args.image]

    # response_format MUST go inside extra_body, NOT at top level
    # Per official docs: "Do not put response_format at the top level"
    extra_body["response_format"] = "url"

    if extra_body:
        payload["extra_body"] = extra_body

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    url = f"{args.base_url}/images/generations"

    # Make API call with retries
    resp = None
    for attempt in range(args.retries):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=600)
            resp.raise_for_status()
            break
        except requests.exceptions.HTTPError as e:
            if attempt < args.retries - 1 and resp is not None and resp.status_code in (429, 503):
                wait = 2 ** (attempt + 1)
                print(f"Retry {attempt + 1}/{args.retries} after {wait}s: HTTP {resp.status_code}", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"Error: API call failed: {e}", file=sys.stderr)
                if resp is not None:
                    print(f"Response: {resp.text}", file=sys.stderr)
                sys.exit(1)
        except Exception as e:
            if attempt < args.retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"Retry {attempt + 1}/{args.retries} after {wait}s: {e}", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"Error: API call failed: {e}", file=sys.stderr)
                sys.exit(1)

    data = resp.json()

    # Extract image URL from response: data[0].url
    image_url = None
    b64_data = None
    if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
        image_url = data["data"][0].get("url")
        b64_data = data["data"][0].get("b64_json")
    elif "url" in data:
        image_url = data["url"]

    # Determine output path
    if not args.output:
        ext = "png"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        args.output = f"agnes_image_{timestamp}.{ext}"

    # Save image: prefer URL download, fall back to base64
    if image_url:
        download_file(image_url, args.output)
    elif b64_data:
        with open(args.output, "wb") as f:
            f.write(base64.b64decode(b64_data))
        print(f"Image saved from base64 to: {args.output}", file=sys.stderr)
    else:
        print(f"Error: No image URL or base64 data in response: {json.dumps(data, indent=2)}", file=sys.stderr)
        sys.exit(1)

    # Output result
    if args.json_output:
        result = {
            "output_path": os.path.abspath(args.output),
            "image_url": image_url,
            "model": args.model,
            "prompt": args.prompt,
            "size": args.size,
            "mode": "image-to-image" if args.image else "text-to-image",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Image saved to: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
