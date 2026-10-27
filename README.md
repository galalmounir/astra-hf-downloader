# astra-hf-downloader

One-node ComfyUI pack: execution-time downloader into models/ subdirs.
Allowlisted hosts only (huggingface / github releases). Made for
Pulsar so models missing from the ComfyUI-Manager DB can be installed
remotely over Tailscale without SSH.

Node: `DownloadToModels` (category `astra`).
Inputs: url (https, allowlisted hosts), dest (models subdir), filename
(optional), overwrite.