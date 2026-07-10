# SPDX-License-Identifier: Apache-2.0

import re
import zipfile
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from dream.intake.models import ParsedSection, SourceSpan

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
DOCX_PARAGRAPH = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
DOCX_TEXT = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"


class IntakeParser:
    def parse(self, path: Path) -> list[ParsedSection]:
        return self.parse_text(self.extract_text(path), source_path=path.as_posix())

    def extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".docx":
            return _docx_text(path)
        if suffix in {".html", ".htm"}:
            return _html_text(path.read_text(encoding="utf-8-sig"))
        return path.read_text(encoding="utf-8-sig")

    @staticmethod
    def parse_text(raw: str, *, source_path: str) -> list[ParsedSection]:
        return parse_markdown(raw, source_path=source_path)


def parse_markdown(raw: str, *, source_path: str) -> list[ParsedSection]:
    raw = raw.lstrip("\ufeff")
    source_lines = raw.splitlines()
    sections: list[ParsedSection] = []
    current_heading = "Overview"
    current_level = 1
    current_start_line = 1
    current_lines: list[str] = []

    def flush(end_line: int) -> None:
        text = "\n".join(current_lines).strip()
        if not text and sections:
            return
        section_number = len(sections) + 1
        section_hash = _section_hash(current_heading, text)
        sections.append(
            ParsedSection(
                section_id=f"section-{section_number}",
                heading=current_heading,
                level=current_level,
                text=text,
                concepts=_concepts(f"{current_heading}\n{text}"),
                source_reference=(
                    f"{source_path}#section-{section_number}:"
                    f"L{current_start_line}-L{max(current_start_line, end_line)}"
                ),
                source_span=SourceSpan(
                    start_line=current_start_line,
                    end_line=max(current_start_line, end_line),
                ),
                section_hash=section_hash,
            )
        )

    for line_number, line in enumerate(source_lines, start=1):
        match = HEADING_RE.match(line.strip())
        if match:
            flush(line_number - 1)
            current_heading = match.group(2).strip()
            current_level = len(match.group(1))
            current_start_line = line_number
            current_lines = []
        else:
            current_lines.append(line)
    flush(len(source_lines))
    return [section for section in sections if section.text or section.heading != "Overview"]


def _concepts(text: str) -> list[str]:
    tokens = [token.lower().replace("_", "-") for token in TOKEN_RE.findall(text)]
    selected = []
    for token in tokens:
        if token in {"the", "and", "for", "with", "from", "this", "that", "when"}:
            continue
        if token not in selected:
            selected.append(token)
        if len(selected) >= 8:
            break
    phrase_rules = {
        "execution status": ("execution", "status"),
        "task status": ("task", "status"),
        "runbook": ("runbook",),
        "architecture": ("architecture",),
        "operator": ("operator",),
    }
    phrases = [
        phrase for phrase, parts in phrase_rules.items() if all(part in tokens for part in parts)
    ]
    return sorted(set(phrases + selected[:6]))


def _section_hash(heading: str, text: str) -> str:
    normalized = "\n".join([heading.strip(), text.strip()]).encode("utf-8")
    return f"sha256:{sha256(normalized).hexdigest()}"


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    paragraphs = []
    for paragraph in root.iter(DOCX_PARAGRAPH):
        text = "".join(node.text or "" for node in paragraph.iter(DOCX_TEXT)).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []
        self.current_tag: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001, ARG002
        self.current_tag = tag.lower()

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self.current_tag in {"h1", "h2", "h3"}:
            level = {"h1": "#", "h2": "##", "h3": "###"}[self.current_tag]
            self.lines.append(f"{level} {text}")
        else:
            self.lines.append(text)


def _html_text(raw: str) -> str:
    parser = _TextHTMLParser()
    parser.feed(raw)
    return "\n\n".join(parser.lines)
