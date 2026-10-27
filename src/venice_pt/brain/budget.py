from __future__ import annotations

from dataclasses import dataclass, field

from venice_pt.contracts.llm import LLMRole


class BudgetExceeded(Exception):
    pass


@dataclass
class BudgetGovernor:
    max_budget_usd: float = 5.0
    downgrade_threshold_pct: float = 0.80  # 80% threshold triggers downgrade to cheap model
    total_spent_usd: float = 0.0
    spend_by_role: dict[LLMRole, float] = field(
        default_factory=lambda: {
            LLMRole.TRIAGE: 0.0,
            LLMRole.PLANNER: 0.0,
            LLMRole.ANALYST: 0.0,
            LLMRole.REPORTER: 0.0,
        }
    )

    def record_spend(self, role: LLMRole, cost_usd: float) -> None:
        self.total_spent_usd = round(self.total_spent_usd + cost_usd, 5)
        self.spend_by_role[role] = round(self.spend_by_role.get(role, 0.0) + cost_usd, 5)

        if self.is_exceeded():
            raise BudgetExceeded(
                f"Engagement budget of ${self.max_budget_usd:.2f} exceeded! "
                f"Total spent: ${self.total_spent_usd:.4f}. Advance directly to REPORT."
            )

    def is_exceeded(self) -> bool:
        return self.total_spent_usd >= self.max_budget_usd

    def should_downgrade(self) -> bool:
        """Returns True if spend has exceeded 80% of budget."""
        return self.total_spent_usd >= (self.max_budget_usd * self.downgrade_threshold_pct)

    def remaining_budget(self) -> float:
        return max(0.0, round(self.max_budget_usd - self.total_spent_usd, 5))
