"""Astra HF Downloader - execution-time model fetch for ComfyUI.

Exposes DownloadToModels: downloads a https URL (Hugging Face / github
releases) into a chosen models/ subdirectory, then reports the placed
filename. Used to install models that are not in the Manager DB.
"""
import os
import tempfile
import time
import urllib.request

MODEL_SUBDIRS = (
    "checkpoints", "diffusion_models", "text_encoders", "vae", "loras",
    "controlnet", "upscale_models", "embeddings", "clip_vision",
    "vae_approx", "clip", "audio_encoders", "style_models",
)

ALLOWED_HOST_SUFFIXES = (
    "huggingface.co", "cdn.huggingface.co", "github.com",
    "objects.githubusercontent.com", "raw.githubusercontent.com",
    "download.pytorch.org",
)


def _models_root() -> str:
    try:
        import folder_paths
        base = folder_paths.models_dir
    except Exception:
        base = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "models"
        )
    return os.path.abspath(base)


class DownloadToModels:
    CATEGORY = "Constellation"
    FUNCTION = "run"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename",)
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "url": ("STRING", {"default": "", "multiline": False}),
                "dest": (MODEL_SUBDIRS,),
                "filename": ("STRING", {"default": ""}),
                "overwrite": (["false", "true"],),
            },
        }

    def run(self, url, dest, filename, overwrite):
        url = (url or "").strip()
        if not url.startswith("https://"):
            raise ValueError(f"only https urls allowed, got: {url[:80]}")
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        if not any(host == h or host.endswith("." + h) for h in ALLOWED_HOST_SUFFIXES):
            raise ValueError(f"host not allowlisted: {host}")

        root = _models_root()
        target_dir = os.path.abspath(os.path.join(root, dest))
        if not target_dir.startswith(root + os.sep):
            raise ValueError(f"dest escapes models dir: {dest}")
        os.makedirs(target_dir, exist_ok=True)

        name = (filename or "").strip() or os.path.basename(urlparse(url).path)
        if not name or "/" in name or ".." in name or name.startswith("."):
            raise ValueError(f"bad filename: {name!r}")
        out_path = os.path.join(target_dir, name)

        if os.path.exists(out_path):
            if overwrite != "true":
                return {"ui": {"text": [f"already-exists: {name}"]}, "result": (name,)}
            os.unlink(out_path)

        req = urllib.request.Request(
            url, headers={"User-Agent": "astra-hf-downloader/0.1"}
        )
        tmp_path = None
        try:
            from comfy.utils import ProgressBar
            pb = None
            with urllib.request.urlopen(req, timeout=14400) as resp, \
                    tempfile.NamedTemporaryFile(
                        dir=target_dir, delete=False, suffix=".part"
                    ) as tmp:
                try:
                    expected = int(resp.headers.get("Content-Length") or 0)
                except (TypeError, ValueError):
                    expected = 0
                if expected > 0:
                    pb = ProgressBar(expected)
                total = 0
                last_report = 0.0
                while True:
                    chunk = resp.read(1 << 22)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    total += len(chunk)
                    if pb is not None:
                        pb.update_absolute(min(total, expected))
                    else:
                        now = time.monotonic()
                        if now - last_report >= 2.0:
                            print(
                                f"[astra-hf-downloader] {name}: {total} bytes"
                                f" (Content-Length unknown)",
                                flush=True,
                            )
                            last_report = now
                tmp_path = tmp.name
            os.replace(tmp_path, out_path)
            tmp_path = None
            print(
                f"[astra-hf-downloader] {name} -> {out_path} ({total} bytes)",
                flush=True,
            )
            return {"ui": {"text": [f"downloaded {total} bytes"]}, "result": (name,)}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


NODE_CLASS_MAPPINGS = {"DownloadToModels": DownloadToModels}
NODE_DISPLAY_NAME_MAPPINGS = {"DownloadToModels": "Model Downloader"}
# Historical ComfyUI attribute spelling (kept for older cores):
NODE_CLASS_MAPPES = NODE_CLASS_MAPPINGS
WEB_DIRECTORY = "./web"