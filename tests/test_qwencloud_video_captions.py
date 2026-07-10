# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
from pathlib import Path

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

    assert len(ranges) >= 10
    assert ranges[0][0] == 0
    assert ranges[-1][1] <= 180
    assert all(start < end for start, end in ranges)
    assert all(ranges[index][1] <= ranges[index + 1][0] for index in range(len(ranges) - 1))
    assert "Qwen Cloud" in text
    assert "Alibaba Cloud" in text
    assert "DREAM" in transcript.read_text(encoding="utf-8-sig")


def test_demo_video_captions_are_in_publication_and_bundle_flow() -> None:
    publication = (ROOT / "scripts" / "qwencloud-video-publication-handoff.ps1").read_text()
    final_bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text()
    devpost_handoff = (ROOT / "scripts" / "qwencloud-devpost-handoff.ps1").read_text()
    handoff_doc = (ROOT / "docs" / "qwencloud-video-upload-handoff.md").read_text()

    assert "CaptionPath = \"docs/qwencloud-demo-video-captions.srt\"" in publication
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

    assert "NarrationCaptionPath" in renderer
    assert "Add-TtsNarration" in renderer
    assert "System.Speech" in renderer
    assert "narrationGenerated" in renderer
    assert "audioCodec" in renderer
