from __future__ import annotations

from pydantic import BaseModel, Field

from venice_pt.contracts.facts import Fact
from venice_pt.contracts.llm import LLMClient, LLMRole, Msg
from venice_pt.exec.runner import ToolResult
from venice_pt.logging import logger


class Interpretation(BaseModel):
    summary: str
    hypotheses: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class Interpreter:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    async def interpret(
        self,
        tool_result: ToolResult,
        facts_extracted: list[Fact],
    ) -> Interpretation:
        """Summarizes tool execution into hypotheses and intelligence."""
        if not self.llm_client:
            s_msg = (
                f"Tool {tool_result.tool} exited with code {tool_result.exit_code}. "
                f"Extracted {len(facts_extracted)} facts."
            )
            return Interpretation(
                summary=s_msg,
                hypotheses=[],
                suggested_actions=[],
            )

        prompt = (
            f"Tool: {tool_result.tool}\n"
            f"Exit Code: {tool_result.exit_code}\n"
            f"Extracted Facts: {[f.key for f in facts_extracted]}\n"
            "Summarize the security implications and formulate hypotheses."
        )

        try:
            res = await self.llm_client.complete(
                role=LLMRole.ANALYST,
                messages=[Msg(role="user", content=prompt)],
                schema=Interpretation,
                max_tokens=512,
            )
            if isinstance(res.parsed, Interpretation):
                return res.parsed
        except Exception as e:
            logger.warning("Interpreter analysis failed", error=str(e))

        return Interpretation(
            summary=f"{tool_result.tool} produced {len(facts_extracted)} facts.",
            hypotheses=[],
            suggested_actions=[],
        )
