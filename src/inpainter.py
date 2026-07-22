import cv2
import numpy as np
import os
from pathlib import Path

try:
    from simple_lama_inpainting import SimpleLama
    HAS_SIMPLE_LAMA = True
except ImportError:
    HAS_SIMPLE_LAMA = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


def get_device(preferred_device=None):
    if not HAS_TORCH:
        return "cpu"
    if preferred_device:
        return preferred_device
    if torch.cuda.is_available():
        return "cuda"
    try:
        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def _find_model_file(path):
    p = Path(path)
    if p.is_file() and p.suffix in [".pt", ".pth", ".ckpt"]:
        return str(p)
    if p.is_dir():
        for ext in [".pt", ".pth", ".ckpt"]:
            candidates = list(p.glob(f"*{ext}"))
            if candidates:
                return str(candidates[0])
    return None


def load_model(model_path=None, device=None):
    if device is None:
        device = get_device()

    local_path = None
    if model_path is None:
        script_dir = Path(__file__).parent
        candidates = [
            script_dir / "models",
            script_dir.parent / "models",
            script_dir.parent.parent / "models",
            Path("models"),
        ]
        for c in candidates:
            found = _find_model_file(c)
            if found:
                local_path = found
                break
    else:
        local_path = _find_model_file(model_path)

    if not HAS_SIMPLE_LAMA:
        raise RuntimeError(
            "simple-lama-inpainting не установлен. Установите:\n"
            "uv pip install simple-lama-inpainting --python .venv\\python.exe"
        )

    print(f"[LaMa] Устройство: {device}")

    if local_path:
        print(f"[LaMa] Локальный файл: {local_path}")
        os.environ["LAMA_MODEL"] = str(local_path)
    else:
        print("[LaMa] Локальный файл не найден. Скачаем автоматически.")

    torch_device = torch.device(device) if HAS_TORCH else "cpu"
    lama = SimpleLama(device=torch_device)

    return {
        "mode": "simple_lama",
        "model": lama,
        "device": str(device),
    }


def inpaint_img_with_lama(img, mask, model=None, device=None):
    if model is None or not isinstance(model, dict) or model.get("mode") != "simple_lama":
        if len(mask.shape) == 3:
            mask = mask[:, :, 0]
        mask_bin = (mask > 127).astype(np.uint8) * 255
        return cv2.inpaint(img, mask_bin, 3, cv2.INPAINT_TELEA)

    lama = model["model"]
    result = lama(img, mask)
    return np.array(result)
