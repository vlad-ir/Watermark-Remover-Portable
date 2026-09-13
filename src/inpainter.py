import cv2
import numpy as np
import os
from pathlib import Path

# Используем проверенную библиотеку simple-lama-inpainting
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

    # --- Поиск локальной модели ---------------------------------------
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

    # --- SimpleLama ---------------------------------------------------
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
    ms = getattr(lama, "max_side", None)
    print(f"[LaMa] Лимит размера: {ms if ms is not None else str(MODEL_SIDE_LIMIT) + ' (наш)'}")

    return {
        "mode": "simple_lama",
        "model": lama,
        "device": str(device),
    }

# Пороговые размеры для отправки изображения в модель целиком
MODEL_SIDE_LIMIT = 2048   # больше этого — обрабатываем фрагментами
CONTEXT_TARGET = 1024     # контекст (px) вокруг каждой области маски
MERGE_DISTANCE = 64       # штрихи маски ближе этого расстояния = один кластер


def _lama_call(lama, img, mask_bin):
    """Прогон через модель + возврат исходного размера, если библиотека ужала"""
    result = np.array(lama(img, mask_bin.astype(np.uint8) * 255))
    if result.shape[:2] != img.shape[:2]:
        result = cv2.resize(result, (img.shape[1], img.shape[0]),
                            interpolation=cv2.INTER_LANCZOS4)
    return result


def inpaint_img_with_lama(img, mask, model=None, device=None, whole_image=False):
    # ---------- Fallback на OpenCV ------------------------------------
    if model is None or not isinstance(model, dict) or model.get("mode") != "simple_lama":
        if len(mask.shape) == 3:
            mask = mask[:, :, 0]
        mask_bin = (mask > 127).astype(np.uint8) * 255
        return cv2.inpaint(img, mask_bin, 3, cv2.INPAINT_TELEA)

    lama = model["model"]

    if len(mask.shape) == 3:
        mask = mask[:, :, 0]
    mask_bin = mask > 127
    if not mask_bin.any():
        return img

    h, w = img.shape[:2]

    # Эффективный лимит: библиотечный, а если он не отчитался — наш
    max_side = getattr(lama, "max_side", None)
    limit = max_side if max_side is not None else MODEL_SIDE_LIMIT

    # ---------- Режим 1: всё изображение целиком ----------------------
    if whole_image and max(h, w) <= limit:
        result = _lama_call(lama, img, mask_bin)
        out = img.copy()
        out[mask_bin] = result[mask_bin]
        return out

    # ---------- Режим 2: фрагменты по кластерам маски ------------------
    # Объединяем близкие штрихи: один водяной знак из нескольких мазков
    # не должен резаться на отдельные куски
    merged = cv2.dilate(mask_bin.astype(np.uint8),
                       np.ones((MERGE_DISTANCE, MERGE_DISTANCE), np.uint8))
    n_clusters, labels = cv2.connectedComponents(merged)

    out = img.copy()
    for cluster_id in range(1, n_clusters):
        ys, xs = np.where(labels == cluster_id)

        pad = 64
        x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
        x1, y1 = min(w, xs.max() + 1 + pad), min(h, ys.max() + 1 + pad)

        # Контекст вокруг кластера: LaMa "видит" окрестность — заливка
        # качественнее, шов незаметнее. Разрешение не меняется.
        long_side = max(x1 - x0, y1 - y0)
        if long_side < CONTEXT_TARGET:
            add = (CONTEXT_TARGET - long_side) // 2
            x0, y0 = max(0, x0 - add), max(0, y0 - add)
            x1, y1 = min(w, x1 + add), min(h, y1 + add)

        crop = img[y0:y1, x0:x1]
        crop_mask = mask_bin[y0:y1, x0:x1]

        # Гигантский кластер (маска на пол-панорамы): ужимаем фрагмент
        # до лимита, иначе зависнем. Платим мягкостью заливки.
        scale = max(x1 - x0, y1 - y0) / limit
        if scale > 1.0:
            crop = cv2.resize(crop, (max(1, int(round((x1 - x0) / scale))),
                                     max(1, int(round((y1 - y0) / scale)))),
                              interpolation=cv2.INTER_AREA)
            crop_mask = cv2.resize(crop_mask.astype(np.uint8),
                                   (crop.shape[1], crop.shape[0]),
                                   interpolation=cv2.INTER_NEAREST) > 0

        result = _lama_call(lama, crop, crop_mask)

        if scale > 1.0:
            result = cv2.resize(result, (x1 - x0, y1 - y0),
                                interpolation=cv2.INTER_LANCZOS4)

        region = out[y0:y1, x0:x1]
        region[mask_bin[y0:y1, x0:x1]] = result[mask_bin[y0:y1, x0:x1]]
    return out
