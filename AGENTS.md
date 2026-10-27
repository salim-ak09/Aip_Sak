# AGENTS.md

## Project
venice-pt — autonomous AI pentest platform. Linux only. Python 3.12.

## Commands
- `make setup`     install dev deps
- `make gate`      lint + typecheck + unit tests — MUST pass before every commit
- `make lab-up`    start local vulnerable targets
- `make test-int`  integration tests against lab
- `make doctor`    verify toolchain

## Hard rules
1. Python 3.12. Type hints on every public function. `from __future__ import annotations`.
2. `mypy --strict` on `contracts/`, `exec/`, `knowledge/`, `brain/`.
3. Subprocess is called ONLY from `exec/runner.py`. Nowhere else.
4. Any data crossing a module boundary MUST be a Pydantic model from `contracts/`.
5. Never change `contracts/` without bumping `CONTRACT_VERSION` and updating `docs/CONTRACTS.md`.
6. Every new tool requires: manifest YAML + parser + golden fixture + unit test.
7. Never write outside `~/.venicept/` and `engagements/`.
8. Unit tests: no network, no root, no real tool execution.
9. Log with structlog. Never `print()` outside `cli/`.
10. Raw tool output NEVER goes into LLM context — only `knowledge/render.py` output.
11. LLM-generated commands MUST be validated against the cached flag schema before execution.
12. Every long operation is checkpointed. Crash must be resumable.
13. No new dependency without adding it to `pyproject.toml` and justifying it in the commit body.
14. If a test fails twice in a row, stop and report — do not loop.

## Workflow
Read `docs/SPEC.md` + `docs/CONTRACTS.md` + the current phase section.
Tests first for deterministic components. Implement. `make gate`. Phase gate. Commit `feat(P<n>): ...`. Report.

## Phase report format
- Phase: P<n>
- Files created/modified
- Tests added (names + what they assert)
- `make gate` output
- Phase gate result
- Blockers / deviations from spec
