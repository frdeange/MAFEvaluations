# Copyright (c) MAFEvaluations project. All rights reserved.

"""Evaluate the multi-agent financial advisory workflow.

Demonstrates two patterns:
1. Post-hoc: Run workflow first, then evaluate the result
2. Run + evaluate: Pass queries and evaluate_workflow() handles both

Both return per-agent breakdowns in sub_results.

Prerequisites:
- Azure AI Foundry project
- Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL in .env

Run:
    python evaluations/06_workflow_eval/run_workflow_eval.py
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
    evals = FoundryEvals(client=client)

    # =========================================================================
    # Pattern 1: Post-hoc — evaluate a workflow run you already did
    # =========================================================================
    print_section("Pattern 1: Post-hoc workflow evaluation")

    workflow, _ = create_financial_workflow(client)
    result = await workflow.run("I have $50,000 and moderate risk tolerance. What should I invest in?")

    eval_results = await evaluate_workflow(
        workflow=workflow,
        workflow_result=result,
        evaluators=evals,
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

    # =========================================================================
    # Pattern 2: Run + evaluate with multiple queries
    # =========================================================================
    print_section("Pattern 2: Run + evaluate with multiple queries")

    workflow2, _ = create_financial_workflow(client)

    eval_results = await evaluate_workflow(
        workflow=workflow2,
        queries=[
            "I'm near retirement with $200,000. Suggest a conservative strategy.",
            "I'm 25, just started working. How should I invest my first $10,000?",
        ],
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

    print_section("Workflow evaluation complete")


if __name__ == "__main__":
    asyncio.run(main())
