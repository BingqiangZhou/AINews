#!/usr/bin/env python3
"""
Transcribe audio with faster-whisper.

Features:
- supports tiny/base/small/medium/large-v2/large-v3
- writes captions.json and transcribe_metadata.json
- prefers CUDA and falls back to CPU automatically
- defaults to non-VAD transcription and can fall back from VAD when explicitly enabled
- uses stability-first decode defaults on CUDA-constrained GPUs
- Progress feedback during transcription
- Workaround for Windows+CUDA CTranslate2 cleanup crash (0xC0000409)
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import subprocess
import sys

# Workaround for CTranslate2 Windows+CUDA cleanup crash (0xC0000409)
# See: https://github.com/SYSTRAN/faster-whisper/issues/71
# The default CUDA async allocator corrupts state during model teardown;
# cub_caching avoids that path. Must be set BEFORE importing faster_whisper.
if sys.platform == "win32":
    os.environ.setdefault("CT2_CUDA_ALLOCATOR", "cub_caching")

import time
import traceback
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional

# Shared pipeline utilities live in the canonical source at
# audio-to-social/scripts/lib/utils.py (the cross-skill shared-scripts hub;
# see AGENTS.md). This skill no longer keeps a local copy — the local empty
# lib/ package was removed so `lib` resolves to audio-to-social's.
_A2S_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "audio-to-social" / "scripts"
sys.path.insert(0, str(_A2S_SCRIPTS))
from lib.utils import load_config, setup_windows_encoding, write_json

MODEL_CHOICES = ["tiny", "base", "small", "medium", "large-v2", "large-v3", "large-v3-turbo"]
SAFE_CUDA_MODELS = {"tiny", "base", "small"}
SAFE_CUDA_VRAM_MB = 4096
SAFE_CUDA_BEAM_SIZE = 5
SAFE_CUDA_BEST_OF = 5
VAD_MIN_SILENCE_DURATION_MS = 500
VAD_SPEECH_PAD_MS = 400
DEFAULT_PIPELINE = "whisper"  # "whisper" or "batched"
RETRY_COOLDOWN_SECONDS = 1.0


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be >= 1")
    return parsed


def _probe_gpu_memory_mb(query_field: str) -> Optional[int]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                f"--query-gpu={query_field}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            check=True,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return int(float(line))
        except ValueError:
            continue
    return None


def probe_gpu_total_memory_mb() -> Optional[int]:
    return _probe_gpu_memory_mb("memory.total")


def probe_gpu_used_memory_mb() -> Optional[int]:
    return _probe_gpu_memory_mb("memory.used")


def is_vad_error(exc: Exception) -> bool:
    error_text = str(exc).lower()
    return "onnxruntime" in error_text or "vad filter" in error_text


def is_cuda_related_error(exc: Exception) -> bool:
    error_text = str(exc).lower()
    patterns = (
        "cuda",
        "cublas",
        "cudnn",
        "out of memory",
        "insufficient memory",
        "resource exhausted",
        "device-side assert",
        "hip error",
    )
    return any(pattern in error_text for pattern in patterns)


def build_transcribe_kwargs(
    *,
    language: Optional[str],
    beam_size: int,
    best_of: int,
    pipeline: str = "whisper",
    batch_size: int = 8,
    initial_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
        "language": language,
        "beam_size": beam_size,
        "best_of": best_of,
        "word_timestamps": True,
    }
    if pipeline == "batched":
        kwargs.update({
            "batch_size": batch_size,
            "vad_filter": True,
            "log_progress": True,
            "vad_parameters": {
                "min_silence_duration_ms": VAD_MIN_SILENCE_DURATION_MS,
                "speech_pad_ms": VAD_SPEECH_PAD_MS,
            },
        })
    if initial_prompt:
        kwargs["initial_prompt"] = initial_prompt
    return kwargs


def _cleanup_model(model: Any, device: str) -> None:
    ct2_model = getattr(model, "model", None)
    if ct2_model is not None and hasattr(ct2_model, "unload_model"):
        try:
            ct2_model.unload_model()
        except Exception as exc:
            print(f"Warning: failed to unload CTranslate2 model cleanly: {exc}")
    gc.collect()
    if device == "cuda":
        time.sleep(RETRY_COOLDOWN_SECONDS)


@contextmanager
def whisper_model_session(
    model: Any, device: str
) -> Generator[Any, None, None]:
    """Context manager that auto-releases a WhisperModel on exit."""
    try:
        yield model
    finally:
        _cleanup_model(model, device)


def cleanup_runtime_memory(device: str, reason: str) -> Optional[int]:
    before_used = probe_gpu_used_memory_mb() if device == "cuda" else None
    gc.collect()
    if device == "cuda":
        time.sleep(RETRY_COOLDOWN_SECONDS)
    after_used = probe_gpu_used_memory_mb() if device == "cuda" else None

    if device == "cuda":
        before_text = "unknown" if before_used is None else f"{before_used}MiB"
        after_text = "unknown" if after_used is None else f"{after_used}MiB"
        print(
            f"GPU cleanup ({reason}): used memory {before_text} -> {after_text}"
        )

    return after_used


def run_transcription_attempt(
    *,
    whisper_model_cls: Any,
    audio_path: str,
    model_size: str,
    language: Optional[str],
    device: str,
    pipeline: str,
    beam_size: int,
    best_of: int,
    batch_size: int = 8,
    compute_type: Optional[str] = None,
    initial_prompt: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    checkpoint_callback: Optional[Callable[[List[Dict[str, Any]], Any], None]] = None,
) -> Dict[str, Any]:
    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "int8"
    cleanup_runtime_memory(device, "before attempt")

    pipeline_name = "BatchedInferencePipeline" if pipeline == "batched" else "WhisperModel"
    vad_info = f"VAD on (min_silence={VAD_MIN_SILENCE_DURATION_MS}ms)" if pipeline == "batched" else "VAD off"
    print(
        f"Attempting transcription with model={model_size}, device={device}, "
        f"{vad_info}, beam_size={beam_size}, best_of={best_of}, "
        f"batch_size={batch_size}, pipeline={pipeline_name}"
    )

    model_load_start = time.time()
    try:
        model = whisper_model_cls(
            model_size,
            device=device,
            compute_type=compute_type,
        )
    except Exception as exc:
        return {
            "success": False,
            "stage": "load",
            "model": model_size,
            "device": device,
            "compute_type": compute_type,
            "pipeline": pipeline,
            "beam_size": beam_size,
            "best_of": best_of,
            "exception": exc,
            "error": str(exc),
            "error_kind": "cuda" if device == "cuda" and is_cuda_related_error(exc) else "other",
            "gpu_memory_after_cleanup_mb": probe_gpu_used_memory_mb() if device == "cuda" else None,
        }

    model_load_time = time.time() - model_load_start
    print(f"Model loaded in {model_load_time:.2f}s")
    print(f"Transcribing audio: {audio_path}")
    print(f"Language: {language or 'auto'}")

    transcribe_start = time.time()
    with whisper_model_session(model, device):
        try:
            if pipeline == "batched":
                from faster_whisper import BatchedInferencePipeline
                batched_pipe = BatchedInferencePipeline(model=model)
                segments, info = batched_pipe.transcribe(
                    audio_path,
                    **build_transcribe_kwargs(
                        language=language,
                        beam_size=beam_size,
                        best_of=best_of,
                        pipeline="batched",
                        batch_size=batch_size,
                        initial_prompt=initial_prompt,
                    ),
                )
            else:
                segments, info = model.transcribe(
                    audio_path,
                    **build_transcribe_kwargs(
                        language=language,
                        beam_size=beam_size,
                        best_of=best_of,
                        pipeline="whisper",
                        initial_prompt=initial_prompt,
                    ),
                )
        except Exception as exc:
            return {
                "success": False,
                "stage": "transcribe",
                "model": model_size,
                "device": device,
                "compute_type": compute_type,
                "pipeline": pipeline,
                "beam_size": beam_size,
                "best_of": best_of,
                "exception": exc,
                "error": str(exc),
                "error_kind": (
                    "vad"
                    if pipeline == "batched" and is_vad_error(exc)
                    else "cuda"
                    if device == "cuda" and is_cuda_related_error(exc)
                    else "other"
                ),
                "model_load_time": model_load_time,
                "gpu_memory_after_release_mb": probe_gpu_used_memory_mb() if device == "cuda" else None,
            }

        captions: List[Dict[str, Any]] = []
        segment_count = 0
        last_progress_time = time.time()

        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue

            segment_count += 1
            words_data = None
            if segment.words:
                words_data = [
                    {
                        "word": w.word,
                        "startMs": int(w.start * 1000),
                        "endMs": int(w.end * 1000),
                        "probability": round(w.probability, 4),
                    }
                    for w in segment.words
                ]

            captions.append(
                {
                    "text": text,
                    "startMs": int(segment.start * 1000),
                    "endMs": int(segment.end * 1000),
                    "timestampMs": None,
                    "confidence": None,
                    "words": words_data,
                }
            )

            current_time = time.time()
            if progress_callback or (current_time - last_progress_time > 5):
                if progress_callback:
                    progress_callback(segment_count, text[:50])
                else:
                    print(f"  Segment {segment_count}: {text[:50]}...")
                last_progress_time = current_time

        if segment_count == 0:
            print(f"Warning: transcription produced 0 segments for {audio_path}")

        if checkpoint_callback:
            try:
                checkpoint_callback(captions, info)
            except Exception as e:
                print(f"Warning: checkpoint save failed: {e}")

    gpu_memory_after_release_mb = probe_gpu_used_memory_mb() if device == "cuda" else None

    transcribe_time = time.time() - transcribe_start
    return {
        "success": True,
        "captions": captions,
        "info": info,
        "model": model_size,
        "device": device,
        "compute_type": compute_type,
        "pipeline": pipeline,
        "beam_size": beam_size,
        "best_of": best_of,
        "model_load_time": model_load_time,
        "transcribe_time": transcribe_time,
        "gpu_memory_after_release_mb": gpu_memory_after_release_mb,
    }


def transcribe_audio(
    audio_path: str,
    model_size: str = "small",
    language: Optional[str] = None,
    device: str = "cuda",
    pipeline: str = DEFAULT_PIPELINE,
    beam_size: int = SAFE_CUDA_BEAM_SIZE,
    best_of: int = SAFE_CUDA_BEST_OF,
    fallback_model: str = "small",
    batch_size: int = 8,
    compute_type: Optional[str] = None,
    initial_prompt: Optional[str] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    checkpoint_callback: Optional[Callable[[List[Dict[str, Any]], Any], None]] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Run faster-whisper and return captions plus metadata.

    Args:
        audio_path: Path to audio file
        model_size: Whisper model size
        language: Language code (None for auto)
        device: 'cuda' or 'cpu'
        pipeline: 'whisper' (sequential, full coverage) or 'batched' (faster, VAD-based)
        beam_size: Decode beam size
        best_of: Number of candidates to sample
        fallback_model: Stable fallback model for retries
        progress_callback: Optional callback(segment_index, text) for progress

    Returns:
        Tuple of (captions list, metadata dict)
    """
    try:
        from faster_whisper import WhisperModel
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "faster_whisper is not installed in the current Python interpreter. "
            f"sys.executable={sys.executable}"
        ) from exc

    overall_start = time.time()
    requested_model = model_size
    requested_device = device
    requested_pipeline = pipeline
    beam_size = max(1, beam_size)
    best_of = max(1, best_of)

    gpu_total_memory_mb = probe_gpu_total_memory_mb() if device == "cuda" else None
    effective_initial_model = requested_model
    fallback_reasons: List[str] = []
    warnings: List[str] = []
    retry_chain: List[Dict[str, Any]] = []

    if device == "cuda":
        if gpu_total_memory_mb is None:
            if requested_model not in SAFE_CUDA_MODELS:
                effective_initial_model = fallback_model
                fallback_reasons.append(
                    "GPU memory could not be detected; using the stable CUDA model "
                    f"{fallback_model} instead of {requested_model}"
                )
        elif gpu_total_memory_mb < SAFE_CUDA_VRAM_MB and requested_model not in SAFE_CUDA_MODELS:
            effective_initial_model = fallback_model
            fallback_reasons.append(
                f"GPU memory {gpu_total_memory_mb}MiB is below the safe CUDA threshold "
                f"{SAFE_CUDA_VRAM_MB}MiB; using {fallback_model} instead of {requested_model}"
            )

    print(f"Loading faster-whisper model: {effective_initial_model}")
    if gpu_total_memory_mb is not None:
        print(f"Detected GPU memory: {gpu_total_memory_mb}MiB")
    elif device == "cuda":
        print("GPU memory detection unavailable; using stability-first CUDA path")

    attempts: deque[Dict[str, Any]] = deque([
        {
            "model": effective_initial_model,
            "device": requested_device,
            "pipeline": requested_pipeline,
            "reason": "initial request",
        }
    ])
    seen_attempts = set()
    last_error: Optional[str] = None

    while attempts:
        attempt = attempts.popleft()
        attempt_key = (
            attempt["model"],
            attempt["device"],
            attempt["pipeline"],
        )
        if attempt_key in seen_attempts:
            continue
        seen_attempts.add(attempt_key)

        attempt_result = run_transcription_attempt(
            whisper_model_cls=WhisperModel,
            audio_path=audio_path,
            model_size=attempt["model"],
            language=language,
            device=attempt["device"],
            pipeline=attempt["pipeline"],
            beam_size=beam_size,
            best_of=best_of,
            batch_size=batch_size,
            compute_type=compute_type,
            initial_prompt=initial_prompt,
            progress_callback=progress_callback,
            checkpoint_callback=checkpoint_callback,
        )

        chain_entry = {
            "attempt": len(retry_chain) + 1,
            "reason": attempt["reason"],
            "model": attempt["model"],
            "device": attempt["device"],
            "pipeline": attempt["pipeline"],
            "beam_size": beam_size,
            "best_of": best_of,
        }

        if attempt_result["success"]:
            info = attempt_result["info"]
            captions = attempt_result["captions"]
            model_load_time = attempt_result["model_load_time"]
            transcribe_time = attempt_result["transcribe_time"]
            total_time = time.time() - overall_start
            warning_text = "; ".join(warnings) if warnings else None
            fallback_reason = "; ".join(fallback_reasons) if fallback_reasons else None

            chain_entry.update(
                {
                    "status": "success",
                    "model_load_time": model_load_time,
                    "transcribe_time": transcribe_time,
                    "captions": len(captions),
                }
            )
            if attempt_result.get("gpu_memory_after_release_mb") is not None:
                chain_entry["gpu_memory_after_release_mb"] = attempt_result[
                    "gpu_memory_after_release_mb"
                ]
            retry_chain.append(chain_entry)

            metadata = {
                "audio_path": audio_path,
                "model": attempt_result["model"],
                "requested_model": requested_model,
                "effective_model": attempt_result["model"],
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "total_captions": len(captions),
                "model_load_time": model_load_time,
                "transcribe_time": transcribe_time,
                "total_time": total_time,
                "device": attempt_result["device"],
                "requested_device": requested_device,
                "compute_type": attempt_result["compute_type"],
                "pipeline": attempt_result["pipeline"],
                "beam_size": beam_size,
                "best_of": best_of,
                "gpu_total_memory_mb": gpu_total_memory_mb,
                "gpu_memory_after_release_mb": attempt_result.get("gpu_memory_after_release_mb"),
                "warning": warning_text,
                "fallback_reason": fallback_reason,
                "retry_chain": retry_chain,
                "python_executable": sys.executable,
            }

            print("\nTranscription completed")
            print(f"  language: {info.language} ({info.language_probability:.2%})")
            print(f"  duration: {info.duration:.2f}s")
            print(f"  captions: {len(captions)}")
            print(f"  model load: {model_load_time:.2f}s")
            print(f"  transcribe: {transcribe_time:.2f}s")
            print(f"  total: {total_time:.2f}s")
            pipeline_label = "BatchedInferencePipeline+VAD" if attempt_result["pipeline"] == "batched" else "WhisperModel"
            print(
                "  model/device: "
                f"{attempt_result['model']} on {attempt_result['device']} "
                f"(requested: {requested_model} on {requested_device})"
            )
            print(f"  pipeline: {pipeline_label}")
            if gpu_total_memory_mb is not None:
                print(f"  gpu memory: {gpu_total_memory_mb}MiB")
            if fallback_reason:
                print(f"  fallback: {fallback_reason}")
            if warning_text:
                print(f"  warning: {warning_text}")

            if info.duration > 0 and transcribe_time > 0:
                rtf = transcribe_time / info.duration
                print(f"  RTF: {rtf:.3f}x ({info.duration / transcribe_time:.1f}x realtime)")

            return captions, metadata

        error_kind = attempt_result["error_kind"]
        error_message = attempt_result["error"]
        last_error = error_message
        chain_entry.update(
            {
                "status": "failed",
                "stage": attempt_result["stage"],
                "error_kind": error_kind,
                "error": error_message,
            }
        )
        if "model_load_time" in attempt_result:
            chain_entry["model_load_time"] = attempt_result["model_load_time"]
        if attempt_result.get("gpu_memory_after_release_mb") is not None:
            chain_entry["gpu_memory_after_release_mb"] = attempt_result[
                "gpu_memory_after_release_mb"
            ]
        if attempt_result.get("gpu_memory_after_cleanup_mb") is not None:
            chain_entry["gpu_memory_after_cleanup_mb"] = attempt_result[
                "gpu_memory_after_cleanup_mb"
            ]
        retry_chain.append(chain_entry)

        print(
            f"Attempt failed during {attempt_result['stage']}: "
            f"{attempt_result['model']} on {attempt_result['device']} ({error_message})"
        )

        if error_kind == "vad" and attempt["pipeline"] == "batched":
            reason = (
                f"VAD failed for {attempt['model']} on {attempt['device']}; "
                f"falling back to WhisperModel pipeline"
            )
            warnings.append(
                "onnxruntime is unavailable or VAD initialization failed; "
                "fell back to WhisperModel pipeline"
            )
            fallback_reasons.append(reason)
            attempts.append(
                {
                    "model": attempt["model"],
                    "device": attempt["device"],
                    "pipeline": "whisper",
                    "reason": reason,
                }
            )
            continue

        if attempt["device"] == "cuda" and attempt["model"] != fallback_model:
            reason = (
                f"CUDA {attempt_result['stage']} failed for {attempt['model']}; "
                f"retrying {fallback_model} on CUDA"
            )
            fallback_reasons.append(reason)
            attempts.append(
                {
                    "model": fallback_model,
                    "device": "cuda",
                    "pipeline": attempt["pipeline"],
                    "reason": reason,
                }
            )
            continue

        if attempt["device"] != "cpu" or attempt["model"] != fallback_model:
            reason = (
                f"{attempt['device'].upper()} {attempt_result['stage']} failed for {attempt['model']}; "
                f"retrying {fallback_model} on CPU"
            )
            fallback_reasons.append(reason)
            attempts.append(
                {
                    "model": fallback_model,
                    "device": "cpu",
                    "pipeline": attempt["pipeline"],
                    "reason": reason,
                }
            )
            continue

    fallback_summary = "; ".join(fallback_reasons) if fallback_reasons else "no fallback executed"
    raise RuntimeError(
        "Transcription failed after retries. "
        f"Last error: {last_error}. Fallbacks: {fallback_summary}"
    )


def build_dynamic_prompt(metadata_path: str) -> str:
    """Build topic-specific initial_prompt from podcast metadata."""
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        if isinstance(meta, dict) and "metadata" in meta:
            meta = meta["metadata"]
        parts = []
        name = meta.get("podcast_name", "")
        title = meta.get("episode_title", "")
        if name:
            parts.append(f"播客《{name}》")
        if title:
            parts.append(f"节目《{title}》")
        if parts:
            prefix = "这是" + "的".join(parts) + "的转录文本"
            return prefix + "，包含逗号、句号和问号。"
    except Exception:
        pass
    return "这是一段标准的中文普通话转录文本，包含逗号、句号和问号。"


def build_parser() -> argparse.ArgumentParser:
    config = load_config()
    default_model = config.get("default_whisper_model", "small")

    parser = argparse.ArgumentParser(
        description="Transcribe audio with faster-whisper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("audio_path", help="Path to the input audio file")
    parser.add_argument(
        "--output",
        "-o",
        help="Output captions JSON path (default: captions.json next to audio)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default=default_model,
        choices=MODEL_CHOICES,
        help=f"Whisper model size (default: {default_model})",
    )
    parser.add_argument(
        "--fallback-model",
        default="small",
        choices=MODEL_CHOICES,
        help="Fallback Whisper model for stability-first retries (default: small)",
    )
    parser.add_argument(
        "--lang",
        "-l",
        default="zh",
        help="Language code, such as auto/zh/en (default: zh)",
    )
    parser.add_argument(
        "--device",
        "-d",
        default="cuda",
        choices=["cuda", "cpu"],
        help="Execution device",
    )
    parser.add_argument(
        "--beam-size",
        type=positive_int,
        default=SAFE_CUDA_BEAM_SIZE,
        help=f"Decode beam size (default: {SAFE_CUDA_BEAM_SIZE})",
    )
    parser.add_argument(
        "--best-of",
        type=positive_int,
        default=SAFE_CUDA_BEST_OF,
        help=f"Number of decode candidates (default: {SAFE_CUDA_BEST_OF})",
    )
    parser.add_argument(
        "--metadata",
        help="Metadata output path (default: transcribe_metadata.json next to audio)",
    )
    parser.add_argument(
        "--vad",
        action="store_true",
        help="Shorthand for --pipeline batched (BatchedInferencePipeline with VAD)",
    )
    parser.add_argument(
        "--pipeline",
        choices=["whisper", "batched"],
        default=DEFAULT_PIPELINE,
        help=f"Transcription pipeline: 'whisper' (sequential, full coverage) or 'batched' (BatchedInferencePipeline with VAD, faster but may drop speech). Default: {DEFAULT_PIPELINE}",
    )
    parser.add_argument(
        "--batch-size",
        type=positive_int,
        default=8,
        help="Batch size for BatchedInferencePipeline (default: 8)",
    )
    parser.add_argument(
        "--compute-type",
        default=None,
        choices=["float16", "int8", "int8_float16", "int8_float32", "float32", "bfloat16", "int8_bfloat16"],
        help="Compute type for ctranslate2 (default: auto — float16 for cuda, int8 for cpu)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rewrite captions and metadata even when both output files exist",
    )
    parser.add_argument(
        "--initial-prompt",
        default=None,
        help="Initial prompt for Whisper to guide punctuation and style (default: Chinese prompt with punctuation)",
    )
    parser.add_argument(
        "--podcast-metadata",
        help="Path to metadata.json for building dynamic initial_prompt (overrides --initial-prompt unless --initial-prompt is explicitly set)",
    )
    return parser


def smooth_word_boundaries(captions: list) -> list:
    """Post-process word-level timestamps to fix gaps and overlaps.

    Returns a new list; does not mutate the input.
    """
    if not captions:
        return captions
    import copy
    captions = copy.deepcopy(captions)
    for cap in captions:
        words = cap.get("words") or []
        if len(words) < 2:
            continue
        for i in range(len(words) - 1):
            curr_end = words[i].get("endMs", 0)
            next_start = words[i + 1].get("startMs", 0)
            gap = next_start - curr_end
            if gap < 20 and gap >= 0:
                mid = (curr_end + next_start) / 2
                words[i]["endMs"] = mid
                words[i + 1]["startMs"] = mid
            elif gap < 0 and abs(gap) > 50:
                overlap = abs(gap)
                split = curr_end - overlap / 2
                words[i]["endMs"] = split
                words[i + 1]["startMs"] = split
    return captions


def main() -> int:
    setup_windows_encoding()
    args = build_parser().parse_args()

    # Dynamic initial_prompt from metadata
    if args.podcast_metadata:
        initial_prompt = build_dynamic_prompt(args.podcast_metadata)
        print(f"Dynamic initial_prompt from metadata: {initial_prompt!r}")
    elif args.initial_prompt:
        initial_prompt = args.initial_prompt
    else:
        initial_prompt = "这是一段标准的中文普通话转录文本，包含逗号、句号和问号。"

    if not os.path.exists(args.audio_path):
        print(f"Error: audio file not found: {args.audio_path}")
        return 1

    audio_dir = os.path.dirname(os.path.abspath(args.audio_path))
    output_path = args.output or os.path.join(audio_dir, "captions.json")
    metadata_path = args.metadata or os.path.join(audio_dir, "transcribe_metadata.json")

    if (
        os.path.exists(output_path)
        and os.path.exists(metadata_path)
        and not args.force
    ):
        print("Reusing existing transcription outputs")
        print(f"captions: {output_path}")
        print(f"metadata: {metadata_path}")
        return 0

    print("\n" + "=" * 50)
    print("Faster-Whisper Audio Transcriber")
    print("=" * 50)
    print(f"audio: {args.audio_path}")
    print(f"model: {args.model}")
    print(f"fallback model: {args.fallback_model}")
    print(f"language: {args.lang}")
    print(f"device: {args.device}")
    print(f"beam_size: {args.beam_size}")
    print(f"best_of: {args.best_of}")
    print(f"output: {output_path}")
    print(f"metadata: {metadata_path}")
    print(f"python: {sys.executable}")
    effective_pipeline = "batched" if args.vad else args.pipeline
    pipeline_label = "BatchedInferencePipeline+VAD" if effective_pipeline == "batched" else "WhisperModel"
    print(f"pipeline: {pipeline_label}")
    if effective_pipeline == "batched":
        print(f"batch_size: {args.batch_size}")
    print(f"compute_type: {args.compute_type or 'auto'}")
    print(f"initial_prompt: {initial_prompt!r}")
    print("=" * 50 + "\n")

    total_start = time.time()

    # Checkpoint callback: saves captions before model cleanup to survive CTranslate2 crash
    _checkpoint_saved = {"captions": False}
    def _save_checkpoint(captions_list, info_obj):
        write_json(captions_list, output_path)
        _checkpoint_saved["captions"] = True
        print(f"[checkpoint] Saved {len(captions_list)} captions to {output_path}")

    try:
        captions, metadata = transcribe_audio(
            args.audio_path,
            model_size=args.model,
            language=None if args.lang == "auto" else args.lang,
            device=args.device,
            pipeline=effective_pipeline,
            beam_size=args.beam_size,
            best_of=args.best_of,
            fallback_model=args.fallback_model,
            batch_size=args.batch_size,
            compute_type=args.compute_type,
            initial_prompt=initial_prompt,
            checkpoint_callback=_save_checkpoint,
        )

        write_json(metadata, metadata_path)

        if not _checkpoint_saved["captions"]:
            write_json(captions, output_path)

        captions = smooth_word_boundaries(captions)
        write_json(captions, output_path)

        total_elapsed = time.time() - total_start
        print(f"\nSaved captions to: {output_path} ({len(captions)} segments)")
        print(f"Saved metadata to: {metadata_path}")
        print(f"Finished in {total_elapsed:.2f}s")
        return 0

    except Exception as exc:
        # If checkpoint was saved but process crashed during cleanup, try to save metadata too
        if _checkpoint_saved["captions"]:
            print(f"\nNote: captions were saved before crash ({output_path})")
            print(f"Re-run without --force to use cached captions, or metadata is lost.")
        print(f"\nError: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
