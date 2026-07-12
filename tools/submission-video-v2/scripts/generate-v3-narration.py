# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import requests

MODEL = "qwen3-tts-instruct-flash-2026-01-26"
VOICE = "Ethan"
DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/api/v1"
BASE_DIRECTION = (
    "A warm American male founder in his early thirties speaking to one technical peer. "
    "Aim for about 132 words per minute with natural breaths, varied rhythm, and small "
    "conversational pauses. Sound thoughtful, curious, and quietly confident. Avoid an "
    "announcer voice, sales energy, corporate training cadence, theatrical emphasis, and "
    "over-enunciation. Do not read punctuation or abbreviations unnaturally."
)


def load_env_file(path: Path | None) -> None:
    if path is None:
        return
    if not path.exists():
        raise FileNotFoundError(f"Environment file not found: {path}")
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def base_url() -> str:
    return os.getenv("QWEN_TTS_API_BASE", DEFAULT_BASE_URL).rstrip("/")


def duration_seconds(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return round(float(completed.stdout.strip()), 6)


def master_audio(source: Path, destination: Path, tempo: float = 1.0) -> None:
    if tempo < 0.8 or tempo > 1.2:
        raise ValueError(f"Narration tempo must be between 0.8 and 1.2: {tempo}")
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-af",
            f"atempo={tempo:.4f},highpass=f=65,loudnorm=I=-16:TP=-1.5:LRA=8,aresample=48000",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(destination),
        ],
        check=True,
    )


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w.%-]+\b", text))


def synthesize(*, text: str, delivery: str, destination: Path) -> dict[str, Any]:
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is required")

    response = requests.post(
        f"{base_url()}/services/aigc/multimodal-generation/generation",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "input": {
                "text": text,
                "voice": VOICE,
                "language_type": "English",
                "instructions": f"{BASE_DIRECTION} Scene direction: {delivery}",
                "optimize_instructions": True,
            },
        },
        timeout=300,
    )
    if not response.ok:
        raise RuntimeError(
            f"DashScope speech synthesis failed with HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    payload = response.json()
    output = payload.get("output", {})
    audio = output.get("audio", {}) if isinstance(output, dict) else {}
    audio_url = audio.get("url") if isinstance(audio, dict) else None
    if not audio_url:
        raise RuntimeError(
            "DashScope speech synthesis returned no audio URL; "
            f"response keys={sorted(payload.keys())}, "
            f"output keys={sorted(output.keys()) if isinstance(output, dict) else []}"
        )

    audio_response = requests.get(audio_url, timeout=180)
    audio_response.raise_for_status()
    destination.write_bytes(audio_response.content)
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    return {
        "request_id": payload.get("request_id"),
        "usage": usage,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate founder-style DREAM V3 narration with Qwen3-TTS Instruct Flash."
    )
    parser.add_argument("--script", type=Path, default=Path("src/v3/narration.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("public/generated/v3"))
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--remaster-only", action="store_true")
    args = parser.parse_args()

    load_env_file(args.env_file)
    all_segments = json.loads(args.script.read_text(encoding="utf-8"))
    selected = set(args.only)
    segments = [item for item in all_segments if not selected or item["id"] in selected]
    if not segments:
        raise RuntimeError(f"No narration segments matched --only values: {sorted(selected)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "narration-manifest.json"
    existing_segments: dict[str, dict[str, Any]] = {}
    if selected and manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing_segments = {
            str(item["id"]): item for item in existing_manifest.get("segments", [])
        }
    manifest_segments: list[dict[str, Any]] = []
    for segment in segments:
        segment_id = str(segment["id"])
        tempo = float(segment.get("tempo", 1.0))
        raw_path = args.output_dir / f"{segment_id}.wav"
        mastered_path = args.output_dir / f"{segment_id}-mastered.wav"
        previous = existing_segments.get(segment_id, {})
        request_metadata: dict[str, Any] = {
            "request_id": previous.get("request_id"),
            "usage": previous.get("usage", {}),
        }

        if args.remaster_only and not raw_path.exists():
            raise FileNotFoundError(f"Raw narration is missing for remaster: {raw_path}")
        if not args.remaster_only and (args.force or not raw_path.exists()):
            request_metadata = synthesize(
                text=str(segment["text"]),
                delivery=str(segment["delivery"]),
                destination=raw_path,
            )
        if args.force or args.remaster_only or not mastered_path.exists():
            master_audio(raw_path, mastered_path, tempo)

        duration = duration_seconds(mastered_path)
        words = word_count(str(segment["text"]))
        manifest_segments.append(
            {
                "id": segment_id,
                "text": segment["text"],
                "delivery": segment["delivery"],
                "tempo": tempo,
                "audio": mastered_path.as_posix(),
                "duration_seconds": duration,
                "word_count": words,
                "effective_wpm": round(words * 60 / duration, 2),
                "sha256": hashlib.sha256(mastered_path.read_bytes()).hexdigest(),
                "request_id": request_metadata.get("request_id"),
                "usage": request_metadata.get("usage", {}),
            }
        )

    if selected and existing_segments:
        replacements = {str(item["id"]): item for item in manifest_segments}
        manifest_segments = [
            replacements.get(str(item["id"]), existing_segments[str(item["id"])])
            for item in all_segments
            if str(item["id"]) in replacements or str(item["id"]) in existing_segments
        ]

    total_seconds = round(sum(item["duration_seconds"] for item in manifest_segments), 6)
    total_words = sum(item["word_count"] for item in manifest_segments)
    manifest = {
        "generator": f"Alibaba Cloud Model Studio {MODEL}",
        "model": MODEL,
        "voice": VOICE,
        "language": "English",
        "instruction_control": True,
        "optimize_instructions": True,
        "base_direction_sha256": hashlib.sha256(BASE_DIRECTION.encode("utf-8")).hexdigest(),
        "segments": manifest_segments,
        "total_voice_seconds": total_seconds,
        "total_words": total_words,
        "effective_wpm": round(total_words * 60 / total_seconds, 2),
        "credentials": {"values_recorded": False},
    }
    manifest_path.write_text(f"{json.dumps(manifest, indent=2)}\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
