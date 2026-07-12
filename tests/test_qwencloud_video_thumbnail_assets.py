# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert data[12:16] == b"IHDR"
    return struct.unpack(">II", data[16:24])


def test_video_thumbnail_asset_is_devpost_ready() -> None:
    png = ROOT / "docs" / "assets" / "qwencloud-video-thumbnail.png"
    component = (
        ROOT
        / "tools"
        / "submission-video-v2"
        / "src"
        / "v3"
        / "GalleryV3.tsx"
    )
    renderer = (
        ROOT
        / "tools"
        / "submission-video-v2"
        / "scripts"
        / "render-v3-gallery.mjs"
    )

    assert png.exists()
    assert component.exists()
    assert renderer.exists()
    assert _png_dimensions(png) == (1280, 720)
    component_text = component.read_text(encoding="utf-8-sig")
    assert "DreamV3Thumbnail" in component_text
    assert "One current truth" in component_text
    assert "generated/arena-final.png" in component_text
    assert "Real Qwen / Function Compute / Tablestore" in component_text
    renderer_text = renderer.read_text(encoding="utf-8-sig")
    assert "canonicalThumbnailPath" in renderer_text
    assert "docs', 'assets', 'qwencloud-video-thumbnail.png" in renderer_text


def test_video_thumbnail_is_in_publication_and_bundle_flow() -> None:
    publication = (ROOT / "scripts" / "qwencloud-video-publication-handoff.ps1").read_text()
    final_bundle = (ROOT / "scripts" / "qwencloud-final-upload-bundle.ps1").read_text()
    handoff = (ROOT / "docs" / "qwencloud-video-upload-handoff.md").read_text()

    assert "ThumbnailPath = \"docs/assets/qwencloud-video-thumbnail.png\"" in publication
    assert "thumbnailSha256" in publication
    assert "Selecting the custom thumbnail transmits" in publication
    assert "video_thumbnail_png" in final_bundle
    assert "video_thumbnail_v3_component" in final_bundle
    assert "video_thumbnail_v3_renderer" in final_bundle
    assert "npm run gallery:v3" in handoff


def test_browser_export_scripts_use_safe_program_files_x86_syntax() -> None:
    scripts = [
        ROOT / "scripts" / "qwencloud-export-video-thumbnail.ps1",
        ROOT / "scripts" / "qwencloud-export-architecture-png.ps1",
        ROOT / "scripts" / "qwencloud-capture-alibaba-proof.ps1",
    ]

    for script in scripts:
        text = script.read_text()
        assert "$env:ProgramFiles(x86)" not in text
        assert "${env:ProgramFiles(x86)}" in text
