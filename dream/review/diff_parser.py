# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field


class DiffSummary(BaseModel):
    files_changed: list[str] = Field(default_factory=list)
    added_line_count: int = 0
    removed_line_count: int = 0
    rough_changed_content: str = ""


def parse_unified_diff(diff_text: str) -> DiffSummary:
    files: list[str] = []
    changed_lines: list[str] = []
    added = 0
    removed = 0

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                files.append(parts[3].removeprefix("b/"))
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
            changed_lines.append(line[1:].strip())
        elif line.startswith("-"):
            removed += 1
            changed_lines.append(line[1:].strip())

    rough_content = "\n".join(line for line in changed_lines if line)[:4000]
    return DiffSummary(
        files_changed=sorted(dict.fromkeys(files)),
        added_line_count=added,
        removed_line_count=removed,
        rough_changed_content=rough_content,
    )
