# Copyright (c) MAFEvaluations project. All rights reserved.

"""Mix local and cloud evaluation in a single evaluate_agent() call.

Demonstrates three patterns:
1. Local-only: Fast, API-free checks
2. Cloud-only: Full Foundry evaluators
3. Mixed: Local + Foundry in one call, returning one EvalResults per provider

Prerequisites:
- Azure AI Foundry project for Pattern 2 and 3
- Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL in .env

Run:
    python evaluations/03_mixed_eval/run_mixed_eval.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import (
    LocalEvaluator,
    evaluate_agent,
    evaluator,
    keyword_check,
    tool_called_check,
)
from agent_framework.foundry import FoundryEvals

from src.agents import create_financial_advisor
from src.utils import create_chat_client


@evaluator
def no_guaranteed_returns(response: str) -> bool:
    """Ensure the agent doesn't promise guaranteed returns."""
    forbidden = ["guaranteed return", "guaranteed profit", "risk-free", "can't lose"]
    return not any(phrase in response.lower() for phrase in forbidden)


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


async def main() -> None:
    client = create_chat_client(provider="foundry")
    agent = create_financial_advisor(client)

    # =========================================================================
    # Pattern 1: Local evaluation only (no API calls, instant)
    # =========================================================================
    print_section("Pattern 1: Local evaluation only")

    local = LocalEvaluator(
        keyword_check("risk", "investment"),
        tool_called_check("get_risk_assessment"),
        no_guaranteed_returns,
    )

    results = await evaluate_agent(
        agent=agent,
        queries=["Use the get_risk_assessment tool for moderate risk level and explain the results"],
        evaluators=local,
    )

    for r in results:
        print(f"Provider: {r.provider}")
        print(f"Results: {r.passed}/{r.total} passed")
        for check_name, counts in r.per_evaluator.items():
            status = "PASS" if counts["failed"] == 0 else "FAIL"
            print(f"  [{status}] {check_name}: {counts['passed']} passed, {counts['failed']} failed")
        if r.all_passed:
            print("[PASS] All local checks passed!")

    # =========================================================================
    # Pattern 2: Foundry evaluation only (cloud-based)
    # =========================================================================
    print_section("Pattern 2: Foundry evaluation only")

    foundry = FoundryEvals(client=client)

    results = await evaluate_agent(
        agent=agent,
        queries=["What's the right investment approach for moderate risk?"],
        evaluators=foundry,
    )

    for r in results:
        print(f"Provider: {r.provider}")
        print(f"Results: {r.passed}/{r.total} passed")
        if r.report_url:
            print(f"Portal: {r.report_url}")
        if r.all_passed:
            print("[PASS] All Foundry evaluators passed")
        else:
            print(f"[FAIL] {r.failed} failed")

    # =========================================================================
    # Pattern 3: Mixed — local + Foundry in one call
    # =========================================================================
    print_section("Pattern 3: Mixed local + Foundry evaluation")

    local = LocalEvaluator(
        keyword_check("investment"),
        no_guaranteed_returns,
    )

    foundry = FoundryEvals(client=client)

    # Pass both as a list — returns one EvalResults per provider
    results = await evaluate_agent(
        agent=agent,
        queries=[
            "Use the get_risk_assessment tool for moderate risk level and explain",
            "Use the search_investment_options tool for the etf category and summarize",
        ],
        evaluators=[local, foundry],
    )

    for r in results:
        status = "PASS" if r.all_passed else "FAIL"
        print(f"  [{status}] {r.provider}: {r.passed}/{r.total} passed")
        for check_name, counts in r.per_evaluator.items():
            print(f"      {check_name}: {counts['passed']}/{counts['passed'] + counts['failed']}")
        if r.report_url:
            print(f"      Portal: {r.report_url}")

    if all(r.all_passed for r in results):
        print("\n[PASS] All checks passed (local + Foundry)!")
    else:
        failed = [r.provider for r in results if not r.all_passed]
        print(f"\n[FAIL] Failed providers: {', '.join(failed)}")


if __name__ == "__main__":
    asyncio.run(main())
