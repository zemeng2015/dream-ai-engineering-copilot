# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TIME_RE = re.compile(
    r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}),(?P<ms>\d{3})"
)


def _to_seconds(value: str) -> float:
    match = TIME_RE.fullmatch(value)
    assert match, value
    return (
        int(match["h"]) * 3600
        + int(match["m"]) * 60
        + int(match["s"])
        + int(match["ms"]) / 1000
    )


def _caption_ranges(path: Path) -> list[tuple[float, float]]:
    ranges: list[tuple[float, float]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if " --> " not in line:
            continue
        start, end = line.split(" --> ", 1)
        ranges.append((_to_seconds(start), _to_seconds(end)))
    return ranges


def test_demo_video_caption_file_is_upload_ready() -> None:
    captions = ROOT / "docs" / "qwencloud-demo-video-captions.srt"
    transcript = ROOT / "docs" / "qwencloud-demo-video-transcript.md"

    assert captions.exists()
    assert transcript.exists()
    text = captions.read_text(encoding="utf-8-sig")
    ranges = _caption_ranges(captions)

    assert len(ranges) == 25
    assert ranges[0][0] == 0
    assert ranges[-1][1] == pytest.approx(143.433)
    assert all(start < end for start, end in ranges)
    assert all(ranges[index][1] <= ranges[index + 1][0] for index in range(len(ranges) - 1))
    assert "Qwen Cloud" in text
    assert "Alibaba Function Compute" in text
    assert "Tablestore transactions" in text
    transcript_text = re.sub(
        r"\s+", " ", transcript.read_text(encoding="utf-8-sig")
    )
    for block in text.strip().split("\n\n"):
        cue = " ".join(block.splitlines()[2:])
        assert cue in transcript_text


def test_demo_video_captions_are_in_publication_and_bundle_flow() -> None:
    publication = (ROOT / "scripts" / "qwencloud-video-publication-handoff.ps1").read_text()
    final_bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text()
    devpost_handoff = (ROOT / "scripts" / "qwencloud-devpost-handoff.ps1").read_text()
    handoff_doc = (ROOT / "docs" / "qwencloud-video-upload-handoff.md").read_text()

    assert "CaptionPath = \"docs/qwencloud-demo-video-captions.srt\"" in publication
    assert "One Current Truth Across Qwen Sessions" in publication
    assert "passed 24/24 cases" in publication
    assert "19 of 64 tokens" in publication
    assert "captionSha256" in publication
    assert "caption/subtitle file transmits" in publication
    assert "demo_video_captions_srt" in final_bundle
    assert "demo_video_transcript" in final_bundle
    assert "demo_video_captions_srt" in devpost_handoff
    assert "docs/qwencloud-demo-video-captions.srt" in handoff_doc


def test_demo_video_renderer_uses_timed_tts_narration() -> None:
    renderer = (ROOT / "scripts" / "qwencloud-render-demo-video.ps1").read_text(
        encoding="utf-8-sig"
    )

    v3_renderer = (
        ROOT / "tools" / "submission-video-v2" / "render-v3.ps1"
    ).read_text(encoding="utf-8-sig")
    generator = (
        ROOT
        / "tools"
        / "submission-video-v2"
        / "scripts"
        / "generate-v3-narration.py"
    ).read_text(encoding="utf-8-sig")

    assert "tools\\submission-video-v2\\render-v3.ps1" in renderer
    assert "dream-qwencloud-devpost-final.mp4" in renderer
    assert "-SkipNarration:$SkipNarration" in renderer
    assert "-SkipCapture:$SkipCapture" in renderer
    assert "validate-v3.mjs" in v3_renderer
    assert "loudnorm=I=-14:TP=-1.5" in v3_renderer
    assert "qwen3-tts-instruct-flash-2026-01-26" in generator
    assert 'VOICE = "Ethan"' in generator
    assert "optimize_instructions" in generator
    assert "System.Speech" not in renderer
    assert "edge-tts" not in renderer
