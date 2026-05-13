# Copyright (c) MAFEvaluations project. All rights reserved.

"""Live-demo variant of the multi-agent workflow evaluation.

Slimmed down from ``run_workflow_eval.py`` so it fits inside a single stage slot
(~60-90 seconds instead of ~4-6 minutes). Trade-offs vs the full version:

- Runs ONLY Pattern 1 (post-hoc evaluation of a single workflow run).
- Pattern 2 (run + evaluate with multiple queries) is dropped.
- Evaluators limited to RELEVANCE + TASK_ADHERENCE instead of the full default set.
  This still produces the per-agent ``sub_results`` breakdown that makes the
  demo interesting — just with two columns instead of seven.

Use this file when presenting live. For the full evaluation suite (more
evaluators, two patterns), use ``run_workflow_eval.py``.

Prerequisites:
- Azure AI Foundry project
- Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL in .env

Run:
    python evaluations/06_workflow_eval/run_workflow_eval_demo.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import evaluate_workflow
from agent_framework.foundry import FoundryEvals

from create_workflow import create_financial_workflow
from src.utils import create_chat_client


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


async def main() -> None:
    client = create_chat_client(provider="foundry")

    print_section("Workflow eval — fast demo (Pattern 1 only, 2 evaluators)")

    workflow, _ = create_financial_workflow(client)
    result = await workflow.run("I have $50,000 and moderate risk tolerance. What should I invest in?")

    eval_results = await evaluate_workflow(
        workflow=workflow,
        workflow_result=result,
        evaluators=FoundryEvals(
            client=client,
            evaluators=[FoundryEvals.RELEVANCE, FoundryEvals.TASK_ADHERENCE],
        ),
    )

    for r in eval_results:
        print(f"\nOverall: {r.status}")
        print(f"  Passed: {r.passed}/{r.total}")
        if r.report_url:
            print(f"  Portal: {r.report_url}")

        print("\nPer-agent breakdown:")
        for agent_name, agent_eval in r.sub_results.items():
            print(f"  {agent_name}: {agent_eval.passed}/{agent_eval.total} passed")
            if agent_eval.report_url:
                print(f"    Portal: {agent_eval.report_url}")

    print_section("Done")


if __name__ == "__main__":
    asyncio.run(main())
