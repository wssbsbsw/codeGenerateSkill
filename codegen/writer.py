from __future__ import annotations

from pathlib import Path
from typing import Dict


def write_project(root_dir: Path, files: Dict[str, str], overwrite: bool = True) -> None:
    for relative_path, content in files.items():
        target = root_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not overwrite:
            continue
        target.write_text(content.rstrip() + "\n", encoding="utf-8")
