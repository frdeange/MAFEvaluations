# Copyright (c) MAFEvaluations project. All rights reserved.

"""Workflow evaluation with the full agent-behaviour evaluator suite.

Extends evaluations/06_workflow_eval with the agent-specific Foundry evaluators
that go beyond the surface-level RELEVANCE / TASK_ADHERENCE pair:

- INTENT_RESOLUTION: did the agent understand what the user wanted?
- TASK_ADHERENCE: did it stay on-task?
- TASK_NAVIGATION_EFFICIENCY: did it take the shortest reasonable route?
- TOOL_CALL_ACCURACY: were the tool calls correct?
- RELEVANCE: bonus surface metric.

These are the same evaluators a Foundry agent gets in the portal, applied
per-agent inside the workflow via ``evaluate_workflow``'s ``sub_results``.
Use this for deep diagnostics — which specialist is the weakest link.

Run:
    python evaluations/10_workflow_deep_eval/run_workflow_deep_eval.py
"""

import asyncio
import sys
from pathlib import Path

# Repo root + 06_workflow_eval folder (for create_workflow.py reuse)
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "evaluations" / "06_workflow_eval"))

from agent_framework import evaluate_workflow
from agent_framework.foundry import FoundryEvals

from create_workflow import create_financial_workflow  # noqa: E402  (sys.path setup)
from src.utils import create_chat_client  # noqa: E402


DEEP_EVALUATORS = [
    FoundryEvals.INTENT_RESOLUTION,
    FoundryEvals.TASK_ADHERENCE,
    FoundryEvals.TOOL_CALL_ACCURACY,
    FoundryEvals.RELEVANCE,
]

# Note: FoundryEvals.TASK_NAVIGATION_EFFICIENCY also exists in v1.3.0, but
# it requires explicit `actions` / `expected_actions` data mapping that the
# SDK does not auto-derive from a workflow run yet. It returns
# 400 MissingRequiredDataMapping today. Once data_mapping plumbing lands in
# the SDK, just add it to this list.


def print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def _print_result(r) -> None:
    print(f"\nOverall: {r.status}")
    print(f"  Total items: {r.passed}/{r.total} passed")
    if getattr(r, "report_url", None):
        print(f"  Portal:    {r.report_url}")

    print("\n  Per-agent breakdown:")
    for agent_name, agent_eval in r.sub_results.items():
        print(f"\n  - {agent_name}: {agent_eval.passed}/{agent_eval.total} passed")
        if getattr(agent_eval, "report_url", None):
            print(f"      Portal: {agent_eval.report_url}")
        if not agent_eval.items:
            continue
        # Show per-evaluator average across all items for this agent
        scores: dict[str, list[float]] = {}
        for item in agent_eval.items:
            for s in item.scores:
                if s.score is None:
                    continue
                scores.setdefault(s.name, []).append(s.score)
        for name, vals in sorted(scores.items()):
            avg = sum(vals) / len(vals)
            print(f"      {name}: avg={avg:.2f} (n={len(vals)})")


async def main() -> None:
    client = create_chat_client(provider="foundry")

    workflow, _ = create_financial_workflow(client)

    queries = [
        "I'm 35, have $100,000 to invest with moderate risk tolerance. What do you recommend?",
        "I'm near retirement with $200,000. Suggest a conservative strategy.",
    ]

    print_section("Deep workflow evaluation (4 agent-behaviour evaluators)")
    print(f"Evaluators: {', '.join(e for e in DEEP_EVALUATORS)}")

    eval_results = await evaluate_workflow(
        workflow=workflow,
        queries=queries,
        evaluators=FoundryEvals(client=client, evaluators=DEEP_EVALUATORS),
        eval_name="MAFEvaluations - Workflow Deep Eval",
    )

    for r in eval_results:
        _print_result(r)

    print_section("Done")


if __name__ == "__main__":
    asyncio.run(main())
