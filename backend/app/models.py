"""Optional, lazy local model adapters.

Models are not required for application startup. Each adapter reports its exact
unavailability rather than downloading weights or treating a score as a verdict.
"""

from functools import lru_cache
from pathlib import Path
from time import perf_counter
import os


TEXT_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
IMAGE_MODEL_ID = "torchvision/mobilenet_v3_small:IMAGENET1K_V1"


def sentence_model_cached() -> bool:
    if os.environ.get('CRISISSENSE_TEXT_MODEL_PATH'):
        return (Path(os.environ['CRISISSENSE_TEXT_MODEL_PATH']) / 'model.safetensors').is_file()
    snapshots = Path.home() / ".cache" / "huggingface" / "hub" / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots"
    return snapshots.is_dir() and any((path / 'model.safetensors').is_file() for path in snapshots.iterdir())


@lru_cache(maxsize=1)
def text_encoder():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError("Sentence encoder runtime is not installed.") from error
    if not sentence_model_cached():
        raise RuntimeError("Sentence encoder weights are not present in the local Hugging Face cache.")
    import torch
    torch.set_num_threads(2)
    try:
        return SentenceTransformer(os.environ.get('CRISISSENSE_TEXT_MODEL_PATH', TEXT_MODEL_ID), device="cpu", local_files_only=True)
    except (OSError, ValueError) as error:
        raise RuntimeError('Local sentence model could not be loaded.') from error


def embed_texts(texts: list[str]) -> tuple[list[list[float]], int]:
    started = perf_counter()
    vectors = text_encoder().encode(texts, batch_size=16, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    return vectors.tolist(), round((perf_counter() - started) * 1000)


@lru_cache(maxsize=1)
def image_encoder():
    try:
        import torch
        from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small
    except ImportError as error:
        raise RuntimeError("MobileNet runtime is not installed.") from error
    weights = MobileNet_V3_Small_Weights.IMAGENET1K_V1
    torch.set_num_threads(2)
    checkpoint = Path(torch.hub.get_dir()) / "checkpoints" / Path(weights.url).name
    if not checkpoint.is_file():
        raise RuntimeError("MobileNetV3-Small weights are not present in the local Torch cache.")
    model = mobilenet_v3_small(weights=None)
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    model.classifier = torch.nn.Identity()
    model.eval()
    return model, weights.transforms()


def image_features(image) -> tuple[int, int]:
    try:
        import torch
    except ImportError as error:
        raise RuntimeError("MobileNet runtime is not installed.") from error
    started = perf_counter()
    model, transform = image_encoder()
    with torch.inference_mode():
        features = model(transform(image.convert("RGB")).unsqueeze(0))
    return int(features.shape[-1]), round((perf_counter() - started) * 1000)


def availability() -> list[dict]:
    entries = [
        {"id": TEXT_MODEL_ID, "task": "semantic retrieval embeddings", "license": "Apache-2.0", "available": False, "reason": "Sentence encoder runtime or approved weights are unavailable."},
        {"id": IMAGE_MODEL_ID, "task": "visual feature extraction", "license": "BSD-style PyTorch/Torchvision distribution; ImageNet weights require separate review", "available": False, "reason": "MobileNet runtime or approved weights are unavailable."},
    ]
    try:
        import sentence_transformers  # noqa: F401
        if sentence_model_cached():
            entries[0]["available"] = True
            entries[0]["reason"] = "Runtime and cached local weights are available."
        else:
            entries[0]["reason"] = "Runtime is installed, but approved local weights are not cached."
    except ImportError:
        pass
    try:
        import torch
        from torchvision.models import MobileNet_V3_Small_Weights
        checkpoint = Path(torch.hub.get_dir()) / "checkpoints" / Path(MobileNet_V3_Small_Weights.IMAGENET1K_V1.url).name
        if checkpoint.is_file():
            entries[1]["available"] = True
            entries[1]["reason"] = "Runtime and cached local weights are available."
        else:
            entries[1]["reason"] = "Runtime is installed, but approved local weights are not cached."
    except ImportError:
        pass
    return entries
