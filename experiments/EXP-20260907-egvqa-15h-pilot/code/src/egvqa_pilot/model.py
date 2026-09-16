"""Local, sequential Qwen3-VL inference with exact request accounting.

The caller owns experiment-wide and per-method ledgers. ``prepare`` runs on CPU
and exposes actual input tokens so the caller can reserve the complete request
before ``generate``. No conversation or KV cache survives a request.
"""

from __future__ import annotations

import dataclasses
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import time
from typing import Any


ROLE_LIMITS = {"answer": 128, "control": 96, "judge": 256}
BACKEND_VERSION = "qwen3vl-pilot-v2-explicit-citation-ids-answer128"
SYSTEM_PROMPT = None  # Experiment prompts are supplied entirely by the runner.


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")
    temporary.replace(path)


@dataclasses.dataclass
class PreparedRequest:
    role: str
    text: str
    inputs: Any
    input_tokens: int
    visual_tokens: int
    text_tokens: int
    max_new_tokens: int
    cache_key: str
    prompt_hash: str
    image_records: list[dict]
    image_grid_thw: list[list[int]]
    preparation_s: float
    model_identity_hash: str
    effective_text: str
    allowed_citation_ids: list[str]


class QwenBackend:
    def __init__(
        self,
        model_path: str | Path = "/root/autodl-tmp/models/Qwen3-VL-8B-Instruct",
        cache_dir: str | Path | None = None,
        max_context_tokens: int = 8192,
        max_images: int = 24,
        seed: int = 17,
    ):
        self.model_path = Path(model_path).expanduser().resolve()
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.max_context_tokens = max_context_tokens
        self.max_images = max_images
        self.seed = seed
        self._processor = None
        self._model = None
        self._identity = None
        self._generation_config = None
        self.model_load_s = None

    @property
    def processor(self):
        if self._processor is None:
            from transformers import AutoProcessor, GenerationConfig
            self._processor = AutoProcessor.from_pretrained(self.model_path, local_files_only=True)
            config = GenerationConfig.from_pretrained(self.model_path, local_files_only=True)
            config.do_sample = False
            config.temperature = None
            config.top_p = None
            config.top_k = None
            config.num_beams = 1
            config.repetition_penalty = 1.0
            config.use_cache = True
            self._generation_config = config
        return self._processor

    def identity(self) -> dict:
        if self._identity is not None:
            return self._identity
        import torch
        processor = self.processor
        files = sorted(
            path for path in self.model_path.iterdir()
            if path.is_file() and path.suffix in {".json", ".safetensors", ".txt"}
        )
        signatures = {path.name: [path.stat().st_size, path.stat().st_mtime_ns] for path in files}
        saved_path = self.cache_dir / "model_file_checksums.json" if self.cache_dir else None
        saved = json.loads(saved_path.read_text()) if saved_path and saved_path.exists() else {}
        if saved.get("local_signatures") == signatures and saved.get("model_path") == str(self.model_path):
            checksums = saved["sha256"]
        else:
            checksums = {path.name: _file_hash(path) for path in files}
            if saved_path:
                _write_json(saved_path, {"model_path": str(self.model_path), "local_signatures": signatures, "sha256": checksums})
        dependencies = {}
        for name in ["torch", "torchvision", "transformers", "accelerate", "Pillow", "numpy", "safetensors", "av"]:
            try:
                dependencies[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                dependencies[name] = None
        identity = {
            "backend_version": BACKEND_VERSION,
            "model_path": str(self.model_path),
            "model_id": "Qwen/Qwen3-VL-8B-Instruct",
            "model_type": "Instruct",
            "revision": None,
            "revision_source": "local asset; complete weight and tokenizer SHA256 manifest",
            "files_sha256": checksums,
            "precision": "bfloat16",
            "quantization": None,
            "attention_implementation": "sdpa",
            "batch_size": 1,
            "seed": self.seed,
            "generation_config": self._generation_config.to_dict(),
            "role_max_new_tokens": ROLE_LIMITS,
            "max_context_tokens": self.max_context_tokens,
            "max_images": self.max_images,
            "processor_class": type(processor).__name__,
            "processor_image_config": processor.image_processor.to_dict(),
            "processor_image_overrides": {"size": {"shortest_edge": 50176, "longest_edge": 50176}},
            "chat_template": processor.chat_template,
            "system_prompt": SYSTEM_PROMPT,
            "answer_citation_manifest": {"rule": "append exact visible image IDs after the answer-role user text",
                "prefix": "Allowed citation IDs: ", "deduplication": "preserve first appearance", "no_images": [],
                "source": "image_records[*].visible_label.id", "roles": ["answer"]},
            "letterbox": {"size": [224, 224], "color": [0, 0, 0], "interpolation": "bicubic", "exif_transpose": True},
            "dependencies": dependencies,
            "cuda_memory_fraction": 0.90,
            "torch_deterministic_algorithms": True,
            "allow_tf32": False,
            "thread_environment": {name: os.environ.get(name) for name in ["OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "TOKENIZERS_PARALLELISM"]},
            "torch_num_threads": torch.get_num_threads(),
            "torch_num_interop_threads": torch.get_num_interop_threads(),
        }
        identity["identity_hash"] = _hash(identity)
        self._identity = identity
        if self.cache_dir:
            _write_json(self.cache_dir / "model_identity.json", identity)
            _write_json(self.cache_dir / "identities" / f"{identity['identity_hash']}.json", identity)
        return identity

    def prepare(self, role: str, text: str, images: list | None = None, max_new_tokens: int | None = None) -> PreparedRequest:
        from PIL import Image, ImageOps
        started = time.monotonic()
        if role not in ROLE_LIMITS:
            raise ValueError(f"Unknown role: {role}")
        if max_new_tokens is None:
            max_new_tokens = ROLE_LIMITS[role]
        if max_new_tokens != ROLE_LIMITS[role]:
            raise ValueError("Role generation limit is frozen; change and re-register configuration before evaluation")
        images = images or []
        if len(images) > self.max_images:
            raise ValueError(f"Image budget exceeded: {len(images)} > {self.max_images}")
        if role == "judge" and images:
            raise ValueError("Offline judge is text-only")
        processor = self.processor
        identity = self.identity()
        content, pil_images, image_records = [], [], []
        for index, entry in enumerate(images):
            if isinstance(entry, dict):
                descriptor = dict(entry)
            elif isinstance(entry, (str, Path)):
                descriptor = {"path": str(entry)}
            else:
                descriptor = {"image": entry}
            path = Path(descriptor["path"]) if descriptor.get("path") else None
            if path is not None:
                with Image.open(path) as source:
                    source_size = list(source.size)
                    rgb = ImageOps.exif_transpose(source).convert("RGB")
                source_sha256 = _file_hash(path)
            else:
                source = descriptor["image"]
                if not isinstance(source, Image.Image):
                    import numpy as np
                    source = np.asarray(source)
                    if source.dtype != np.uint8 or source.ndim != 3 or source.shape[-1] != 3:
                        raise ValueError("In-memory images must be RGB uint8 H x W x 3 arrays")
                    source = Image.fromarray(source)
                source_size = list(source.size)
                rgb = ImageOps.exif_transpose(source).convert("RGB")
                source_sha256 = hashlib.sha256(rgb.tobytes()).hexdigest()
            if rgb.size == (224, 224):
                picture = rgb.copy()
            else:
                picture = ImageOps.pad(rgb, (224, 224), method=Image.Resampling.BICUBIC, color=(0, 0, 0), centering=(0.5, 0.5))
            label = {key: descriptor[key] for key in ["id", "group_id", "capsule_id", "pts", "timestamp", "source_id"] if key in descriptor}
            if not label:
                label = {"id": f"image-{index + 1}"}
            # Only caller-approved visible identifiers/times are passed to the model.
            content.append({"type": "text", "text": _json(label)})
            content.append({"type": "image"})
            pil_images.append(picture)
            image_records.append({
                "index": index,
                "path": str(path) if path is not None else None,
                "source_size": source_size,
                "letterbox_size": [224, 224],
                "source_sha256": source_sha256,
                "rgb_sha256": hashlib.sha256(picture.tobytes()).hexdigest(),
                "visible_label": label,
            })
        allowed_ids = list(dict.fromkeys(record["visible_label"]["id"] for record in image_records if "id" in record["visible_label"]))
        effective_text = text + "\nAllowed citation IDs: " + _json(allowed_ids) if role == "answer" else text
        content.append({"type": "text", "text": effective_text})
        messages = [{"role": "user", "content": content}]
        rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        kwargs = {"text": [rendered], "return_tensors": "pt", "truncation": False}
        if pil_images:
            kwargs.update(images=pil_images, images_kwargs={"size": {"shortest_edge": 50176, "longest_edge": 50176}})
        inputs = processor(**kwargs)
        input_tokens = int(inputs["input_ids"].shape[-1])
        image_token_id = processor.tokenizer.convert_tokens_to_ids("<|image_pad|>")
        visual_tokens = int((inputs["input_ids"] == image_token_id).sum().item())
        grids = inputs["image_grid_thw"].tolist() if "image_grid_thw" in inputs else []
        patch = int(processor.image_processor.patch_size)
        for image_record, grid in zip(image_records, grids):
            image_record["processor_size"] = [grid[2] * patch, grid[1] * patch]
            image_record["visual_tokens"] = grid[0] * grid[1] * grid[2] // (processor.image_processor.merge_size ** 2)
        if input_tokens + max_new_tokens > self.max_context_tokens:
            raise ValueError(f"Token budget exceeded before inference: {input_tokens} + {max_new_tokens} > {self.max_context_tokens}")
        request_key = {
            "model_identity_hash": identity["identity_hash"], "role": role,
            "rendered_prompt": rendered,
            "images": [{key: value for key, value in record.items() if key != "path"} for record in image_records],
            "max_new_tokens": max_new_tokens,
        }
        return PreparedRequest(role, text, inputs, input_tokens, visual_tokens, input_tokens - visual_tokens,
                               max_new_tokens, _hash(request_key), _hash(rendered), image_records,
                               grids, time.monotonic() - started, identity["identity_hash"], effective_text, allowed_ids)

    def cache_lookup(self, prepared: PreparedRequest) -> dict | None:
        if self.cache_dir is None:
            return None
        path = self.cache_dir / "responses" / f"{prepared.cache_key}.json"
        if not path.exists():
            return None
        value = json.loads(path.read_text())
        if value.get("cache_key") != prepared.cache_key or value.get("error"):
            return None
        return value

    def load(self) -> None:
        if self._model is not None:
            return
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        import torch
        from transformers import Qwen3VLForConditionalGeneration, set_seed
        self.identity()
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is required for this registered pilot backend")
        set_seed(self.seed)
        torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.cuda.set_per_process_memory_fraction(0.90, 0)
        started = time.monotonic()
        self._model = Qwen3VLForConditionalGeneration.from_pretrained(
            self.model_path, dtype=torch.bfloat16, device_map={"": "cuda:0"},
            attn_implementation="sdpa", low_cpu_mem_usage=True, local_files_only=True,
        ).eval()
        self._model.generation_config = self._generation_config
        torch.cuda.synchronize()
        self.model_load_s = time.monotonic() - started

    def generate(self, role: str | None = None, text: str | None = None, images: list | None = None,
                 request_id: str = "", metadata: dict | None = None, max_new_tokens: int | None = None,
                 prepared: PreparedRequest | None = None, use_cache: bool = True) -> dict:
        if prepared is None:
            prepared = self.prepare(role, text, images, max_new_tokens)
        elif role is not None and role != prepared.role:
            raise ValueError("Prepared request role mismatch")
        if use_cache:
            cached = self.cache_lookup(prepared)
            if cached is not None:
                return {**cached, "request_id": request_id, "metadata": metadata or {}, "cache_hit": True,
                        "physical_request": False, "physical_latency_s": 0.0, "original_request_id": cached.get("request_id")}
        import torch
        record = {
            "request_id": request_id, "metadata": metadata or {}, "role": prepared.role,
            "cache_key": prepared.cache_key, "model_identity_hash": prepared.model_identity_hash,
            "prompt_hash": prepared.prompt_hash, "input_text": prepared.text,
            "effective_user_text": prepared.effective_text, "allowed_citation_ids": prepared.allowed_citation_ids,
            "input_tokens": prepared.input_tokens, "visual_tokens": prepared.visual_tokens,
            "text_tokens": prepared.text_tokens, "max_new_tokens": prepared.max_new_tokens,
            "image_records": prepared.image_records, "image_grid_thw": prepared.image_grid_thw,
            "preparation_s": prepared.preparation_s, "cache_hit": False, "physical_request": False,
            "output_text": "", "output_tokens": 0, "output_token_ids": [], "truncated": False,
            "output_tokens_complete": True,
            "error": None, "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "torch_num_threads": torch.get_num_threads(), "torch_num_interop_threads": torch.get_num_interop_threads(),
        }
        started = time.monotonic()
        device_inputs = generated = None
        try:
            self.load()
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
            free_before, total_memory = torch.cuda.mem_get_info()
            gpu_properties = torch.cuda.get_device_properties(0)
            record["gpu_name"] = gpu_properties.name
            record["gpu_compute_capability"] = [gpu_properties.major, gpu_properties.minor]
            record["torch_cuda_version"] = torch.version.cuda
            external_bytes = max(0, total_memory - free_before - torch.cuda.memory_reserved())
            device_inputs = prepared.inputs.to(self._model.device)
            # No past_key_values argument and no persistent generation state.
            generation_started = time.monotonic()
            record["physical_request"] = True
            with torch.inference_mode():
                generated = self._model.generate(**device_inputs, max_new_tokens=prepared.max_new_tokens, do_sample=False)
            torch.cuda.synchronize()
            record["generation_s"] = time.monotonic() - generation_started
            output = generated[0, prepared.input_tokens:].tolist()
            record["output_token_ids"] = output
            record["output_tokens"] = len(output)
            record["output_text"] = self.processor.tokenizer.decode(output, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            eos = self._generation_config.eos_token_id
            eos_ids = set(eos if isinstance(eos, list) else [eos])
            record["truncated"] = len(output) >= prepared.max_new_tokens and (not output or output[-1] not in eos_ids)
            record["finish_reason"] = "length" if record["truncated"] else "stop"
            record["peak_cuda_allocated_bytes"] = torch.cuda.max_memory_allocated()
            record["peak_cuda_reserved_bytes"] = torch.cuda.max_memory_reserved()
            record["peak_device_used_bytes_estimate"] = external_bytes + torch.cuda.max_memory_reserved()
            record["gpu_total_memory_bytes"] = total_memory
            record["memory_limit_exceeded"] = record["peak_device_used_bytes_estimate"] > total_memory * 0.90
            if record["memory_limit_exceeded"]:
                record["error"] = "Peak device memory estimate exceeded the registered 90% limit"
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
            record["finish_reason"] = "error"
            record["output_tokens_complete"] = False
            # A interrupted generation may have produced unobserved tokens. The
            # outer ledger must conservatively retain the maximum reservation.
            record["conservative_output_tokens"] = prepared.max_new_tokens if record["physical_request"] else 0
            if torch.cuda.is_available():
                record["peak_cuda_allocated_bytes"] = torch.cuda.max_memory_allocated()
                record["peak_cuda_reserved_bytes"] = torch.cuda.max_memory_reserved()
        finally:
            device_inputs = generated = None
            # BatchFeature.to mutates in place; put the prepared payload back on
            # CPU so callers retaining it do not keep visual tensors on the GPU.
            prepared.inputs = prepared.inputs.to("cpu")
        record["total_tokens"] = record["input_tokens"] + record["output_tokens"]
        record["latency_s"] = time.monotonic() - started
        record["physical_latency_s"] = record["latency_s"]
        record["model_load_s"] = self.model_load_s
        if self.cache_dir and not record["error"]:
            _write_json(self.cache_dir / "responses" / f"{prepared.cache_key}.json", record)
        return record

    def unload(self) -> None:
        self._model = None
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
