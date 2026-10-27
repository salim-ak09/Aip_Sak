from __future__ import annotations

import asyncio
import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from venice_pt.brain.budget import BudgetGovernor
from venice_pt.config import config
from venice_pt.contracts.llm import LLMResult, LLMRole, Msg
from venice_pt.logging import logger

T = TypeVar("T", bound=BaseModel)

ROLE_MODELS = {
    LLMRole.TRIAGE: "gpt-4o-mini",
    LLMRole.PLANNER: "gpt-4o",
    LLMRole.ANALYST: "gpt-4o",
    LLMRole.REPORTER: "gpt-4o",
}

DOWNGRADE_MODEL = "gpt-4o-mini"

PRICING_PER_1K = {
    "gpt-4o-mini": {"in": 0.00015, "out": 0.0006},
    "gpt-4o": {"in": 0.005, "out": 0.015},
}


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        budget_governor: BudgetGovernor | None = None,
    ) -> None:
        self.api_base = (api_base or config.llm_api_base).rstrip("/")
        self.api_key = api_key or config.llm_api_key or "sk-dummy"
        self.budget_governor = budget_governor or BudgetGovernor()

    async def complete(
        self,
        role: LLMRole,
        messages: list[Msg],
        schema: type[T] | None = None,
        max_tokens: int = 2048,
    ) -> LLMResult:
        model = ROLE_MODELS.get(role, "gpt-4o")
        if self.budget_governor.should_downgrade():
            logger.warning(
                "Budget threshold reached (>80%). Downgrading model to cheap tier.",
                original_model=model,
            )
            model = DOWNGRADE_MODEL

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
        }

        if schema:
            payload["response_format"] = {"type": "json_object"}

        t0 = time.perf_counter()
        retries = 3
        delay = 1.0

        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self.api_base}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    choice = data["choices"][0]["message"]
                    raw_text = choice.get("content", "")
                    usage = data.get("usage", {})
                    tokens_in = usage.get("prompt_tokens", 0)
                    tokens_out = usage.get("completion_tokens", 0)

                    rates = PRICING_PER_1K.get(model, PRICING_PER_1K["gpt-4o-mini"])
                    cost_usd = round(
                        (tokens_in / 1000.0) * rates["in"] + (tokens_out / 1000.0) * rates["out"],
                        5,
                    )

                    self.budget_governor.record_spend(role, cost_usd)

                    parsed_obj: T | None = None
                    if schema:
                        try:
                            parsed_obj = schema.model_validate_json(raw_text)
                        except Exception as ve:
                            logger.warning("Failed to parse LLM structured output", error=str(ve))

                    latency_ms = int((time.perf_counter() - t0) * 1000)
                    return LLMResult(
                        text=raw_text,
                        parsed=parsed_obj,
                        model=model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        cost_usd=cost_usd,
                        latency_ms=latency_ms,
                    )

            except Exception as e:
                if attempt == retries - 1:
                    logger.error("LLM call failed after retries", error=str(e), role=role.value)
                    raise
                await asyncio.sleep(delay)
                delay *= 2

        raise RuntimeError("Unexpected LLM client loop termination")
