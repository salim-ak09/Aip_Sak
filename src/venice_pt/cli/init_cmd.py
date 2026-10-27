from __future__ import annotations

import re
from pathlib import Path

import yaml
from rich.console import Console

from venice_pt.config import config

console = Console()


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\-_.]", "_", text.strip().lower())
    return re.sub(r"_+", "_", slug).strip("_")


def init_engagement(
    name: str | None = None,
    target: str = "http://127.0.0.1:3000",
) -> Path:
    slug = slugify(name or target)
    eng_dir = config.engagements_dir / slug
    eng_dir.mkdir(parents=True, exist_ok=True)
    (eng_dir / "artifacts").mkdir(parents=True, exist_ok=True)

    scope_file = eng_dir / "scope.yaml"
    if not scope_file.exists():
        host = target.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0]
        scope_data = {
            "target": target,
            "include": {
                "domains": [host] if not host.replace(".", "").isdigit() else [],
                "cidrs": [f"{host}/32"] if host.replace(".", "").isdigit() else [],
            },
            "exclude": {
                "domains": [],
                "cidrs": [],
            },
        }
        scope_file.write_text(yaml.dump(scope_data, sort_keys=False), encoding="utf-8")

    console.print(f"[bold green]Initialized engagement workspace at:[/bold green] {eng_dir}")
    return eng_dir
