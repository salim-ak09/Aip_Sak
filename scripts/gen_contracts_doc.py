from __future__ import annotations

import inspect
from pathlib import Path

from venice_pt import contracts
from venice_pt.contracts.events import CONTRACT_VERSION


def generate_contracts_doc() -> str:
    lines: list[str] = [
        "# Venice-PT Data Contracts Reference",
        "",
        f"**Contract Version:** `{CONTRACT_VERSION}` (FROZEN)",
        "",
        "This document is automatically generated from `src/venice_pt/contracts/`.",
        "",
        "---",
        "",
    ]

    modules = [
        ("events", contracts.events),
        ("tools", contracts.tools),
        ("facts", contracts.facts),
        ("decisions", contracts.decisions),
        ("findings", contracts.findings),
        ("llm", contracts.llm),
    ]

    for mod_name, mod in modules:
        lines.append(f"## Module: `venice_pt.contracts.{mod_name}`")
        lines.append("")
        for name, obj in inspect.getmembers(mod):
            if inspect.isclass(obj) and obj.__module__ == mod.__name__:
                lines.append(f"### `{name}`")
                doc = inspect.getdoc(obj)
                if doc:
                    lines.append(f"{doc}")
                lines.append("")
                # If BaseModel, list fields
                if hasattr(obj, "model_fields"):
                    lines.append("| Field | Type | Required / Default |")
                    lines.append("|---|---|---|")
                    for fname, ffield in obj.model_fields.items():
                        req = "Required" if ffield.is_required() else f"`{ffield.default}`"
                        lines.append(f"| `{fname}` | `{ffield.annotation}` | {req} |")
                    lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    doc_content = generate_contracts_doc()
    target_path = Path(__file__).resolve().parent.parent / "docs" / "CONTRACTS.md"
    if "--check" in sys.argv:
        if not target_path.exists():
            print("docs/CONTRACTS.md does not exist.")
            sys.exit(1)
        current = target_path.read_text(encoding="utf-8")
        if current.strip() != doc_content.strip():
            print("docs/CONTRACTS.md is out of sync with contracts.")
            sys.exit(1)
        print("docs/CONTRACTS.md is up to date.")
    else:
        target_path.write_text(doc_content, encoding="utf-8")
        print(f"Generated {target_path}")
