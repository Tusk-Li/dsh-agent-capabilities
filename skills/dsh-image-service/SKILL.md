---
name: dsh-image-service
description: Generate or edit raster images through a configured HTTP image API; check configuration when the user asks for image generation.
---

Use `scripts/image_service.py` relative to this skill directory, through the ordinary PowerShell tool. Obtain the bundled Python interpreter using `load_workspace_dependencies`; do not assume the Windows `python` alias is an interpreter.

Run `status --config <config>` first. The default configuration is `.dsh/image-service.json` in the current workspace. `status` checks configuration and whether the named credential environment variable exists, without making a paid request or showing its value. Copy `image-service.example.json` beside the script to that path when configuration is needed. Ask for the service endpoint/model and have credentials configured locally; do not ask users to paste keys into chat. DSH-managed model credentials are not automatically environment variables.

The adapter accepts an OpenAI-compatible images protocol: JSON generation request; multipart image edit; response `data[].b64_json`. Set full endpoint URLs, model, and the name of the credential environment variable. Extra provider fields belong in `requestOptions`. A service returning only image URLs requires an appropriate response-format setting or another adapter; do not claim such a response generated a saved file.

Generate: `image_service.py generate --config <config> --prompt <text> --output-dir <workspace>/outputs`.
Edit: `image_service.py edit --config <config> --prompt <text> --image <path> [--mask <path>] --output-dir <workspace>/outputs`.
Optional generation/edit arguments: `--size 1024x1024`, `--count 1`. Results report absolute file paths. Inspect files before delivery. Preserve the requested transparency and describe provider limitations accurately. Never substitute SVG or a mock response for a requested raster image.

The script enforces HTTPS except explicit loopback development mode, rejects empty/invalid configurations, bounds image counts and response sizes, validates image signatures, and creates new output files without overwriting existing files. Let the shell tool enforce permissions. Do not retry paid generation automatically after an uncertain network outcome.
