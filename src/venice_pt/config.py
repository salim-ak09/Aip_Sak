from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VeniceConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VENICEPT_",
        env_file=".env",
        extra="ignore",
    )

    home_dir: Path = Field(default_factory=lambda: Path.home() / ".venicept")
    toolchain_dir: Path = Field(default_factory=lambda: Path.home() / ".venicept" / "toolchain")
    engagements_dir: Path = Field(default_factory=lambda: Path("engagements"))
    default_risk_ceiling: int = 1
    default_budget_usd: float = 5.0
    llm_provider: str = "openai"  # openai, gemini, ollama, custom
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    gemini_api_key: str | None = None
    default_model: str = "gpt-4o"

    def ensure_directories(self) -> None:
        self.home_dir.mkdir(parents=True, exist_ok=True)
        (self.home_dir / "flags").mkdir(parents=True, exist_ok=True)
        (self.toolchain_dir / "bin").mkdir(parents=True, exist_ok=True)
        self.engagements_dir.mkdir(parents=True, exist_ok=True)


config = VeniceConfig()
