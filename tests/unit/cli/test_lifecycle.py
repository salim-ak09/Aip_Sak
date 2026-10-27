from __future__ import annotations

from pathlib import Path

import pytest

from venice_pt.brain.checkpoint import Checkpoint
from venice_pt.cli.init_cmd import init_engagement, slugify
from venice_pt.cli.run_cmd import run_engagement
from venice_pt.config import config
from venice_pt.contracts.events import Phase


def test_slugify() -> None:
    assert slugify("http://localhost:3000") == "http_localhost_3000"
    assert slugify("My Engagement #1") == "my_engagement_1"


def test_init_engagement_workspace(tmp_path: Path) -> None:
    orig_eng = config.engagements_dir
    config.engagements_dir = tmp_path / "engagements"

    try:
        eng_dir = init_engagement("test_init", "http://127.0.0.1:3000")
        assert eng_dir.exists()
        assert (eng_dir / "scope.yaml").exists()
        assert (eng_dir / "artifacts").exists()
    finally:
        config.engagements_dir = orig_eng


def test_checkpoint_save_and_load(tmp_path: Path) -> None:
    chk_file = tmp_path / "state.json"
    chk = Checkpoint(
        engagement_id="chk_test",
        target="127.0.0.1",
        current_phase=Phase.RECON,
        completed_phases=[Phase.SCOPE],
        status="running",
    )
    chk.save(chk_file)

    loaded = Checkpoint.load(chk_file)
    assert loaded is not None
    assert loaded.engagement_id == "chk_test"
    assert loaded.current_phase == Phase.RECON
    assert Phase.SCOPE in loaded.completed_phases


@pytest.mark.asyncio
async def test_run_engagement_lifecycle(tmp_path: Path) -> None:
    orig_eng = config.engagements_dir
    config.engagements_dir = tmp_path / "engagements"

    try:
        await run_engagement(
            target="http://127.0.0.1:3000",
            engagement_name="unit_run",
            phases_filter="scope,recon",
        )

        eng_dir = config.engagements_dir / "unit_run"
        assert (eng_dir / "events.db").exists()
        assert (eng_dir / "state.json").exists()

        chk = Checkpoint.load(eng_dir / "state.json")
        assert chk is not None
        assert chk.status == "completed"
    finally:
        config.engagements_dir = orig_eng
