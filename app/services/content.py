from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

CONTENT_FILE = Path("data/content.json")


def load_content() -> dict[str, Any]:
    if not CONTENT_FILE.exists():
        return {}
    return json.loads(CONTENT_FILE.read_text(encoding="utf-8"))


def save_content(section: str, data: dict[str, Any]) -> None:
    content = load_content()
    content[section] = data
    CONTENT_FILE.parent.mkdir(exist_ok=True, parents=True)
    CONTENT_FILE.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def get_section(section: str, default: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    content = load_content()
    return content.get(section, default or {})
