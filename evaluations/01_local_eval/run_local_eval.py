# Copyright (c) MAFEvaluations project. All rights reserved.

"""Local evaluation — no API calls, instant results, CI-friendly.

Demonstrates three patterns:
1. Built-in checks: keyword_check, tool_called_check
2. Custom @evaluator decorated functions
3. Expected tool calls with tool_calls_present and tool_call_args_match

Run:
    python evaluations/01_local_eval/run_local_eval.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import (
    ExpectedToolCall,
    LocalEvaluator,
    evaluate_agent,
    evaluator,
    keyword_check,
    tool_call_args_match,
    tool_called_check,
    tool_calls_present,
)

from src.agents import create_financial_advisor
from src.utils import create_chat_client


# ---------------------------------------------------------------------------
# Custom evaluator functions (Pattern 2)
# ---------------------------------------------------------------------------

@evaluator
def mentions_disclaimer(response: str) -> bool:
    """Check that the response includes some form of disclaimer."""
    disclaimer_phrases = [
        "not personalized advice",
        "consult with a",
        "licensed financial advisor",
        "general information",
        "not a recommendation",
        "professional advice",
        "disclaimer",
    ]
    response_lower = response.lower()
    return any(phrase in response_lower for phrase in disclaimer_phrases)


@evaluator
def response_not_empty(response: str) -> bool:
    """Check that the response is not empty or trivially short."""
    return len(response.strip()) > 20


@evaluator
def no_specific_stock_tips(response: str) -> bool:
    """Check that the agent does not give explicit buy/sell stock recommendations."""
    forbidden_phrases = [
        "you should buy",
        "i recommend buying",
        "buy this stock",
        "sell this stock",
        "guaranteed return",
        "guaranteed profit",
        "can't lose",
        "risk-free investment",
    ]
    response_lower = response.lower()
    return not any(phrase in response_lower for phrase in forbidden_phrases)


@evaluator(name="response_length_check")
def response_length_ok(response: str) -> dict:
    """Check response length is reasonable (50-5000 chars) and return a score."""
    length = len(response)
    if 50 <= length <= 5000:
        return {"passed": True, "reason": f"Response length {length} is within range"}
    return {"passed": False, "reason": f"Response length {length} outside range [50, 5000]"}


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


async def main() -> None:
    client = create_chat_client()
    agent = create_financial_advisor(client)

    # =========================================================================
    # Pattern 1: Built-in checks (keyword_check, tool_called_check)
    # =========================================================================
    print_section("Pattern 1: Built-in checks")

    local = LocalEvaluator(
        keyword_check("C001"),
        tool_called_check("get_portfolio_summary"),
    )

    results = await evaluate_agent(
        agent=agent,
        queries=["Show me the portfolio summary for client C001"],
        evaluators=local,
    )

    for r in results:
        print(f"Provider: {r.provider}")
        print(f"Status: {r.status}")
        print(f"Results: {r.passed}/{r.total} passed")
        for check_name, counts in r.per_evaluator.items():
            status = "PASS" if counts["failed"] == 0 else "FAIL"
            print(f"  [{status}] {check_name}: {counts['passed']} passed, {counts['failed']} failed")

    # =========================================================================
    # Pattern 2: Custom @evaluator decorated functions
    # =========================================================================
    print_section("Pattern 2: Custom @evaluator functions")

    custom_local = LocalEvaluator(
        mentions_disclaimer,
        response_not_empty,
        no_specific_stock_tips,
        response_length_ok,
    )

    results = await evaluate_agent(
        agent=agent,
        queries=[
            "What investment strategy do you recommend for someone in their 30s?",
            "Should I invest in cryptocurrency?",
        ],
        evaluators=custom_local,
    )

    for r in results:
        print(f"Provider: {r.provider}")
        print(f"Results: {r.passed}/{r.total} passed")
        for check_name, counts in r.per_evaluator.items():
            status = "PASS" if counts["failed"] == 0 else "FAIL"
            print(f"  [{status}] {check_name}: {counts['passed']} passed, {counts['failed']} failed")

        if r.all_passed:
            print("[PASS] All custom checks passed!")
        else:
            print(f"[FAIL] {r.failed} items failed")

    # =========================================================================
    # Pattern 3: Expected tool calls (tool_calls_present, tool_call_args_match)
    # =========================================================================
    print_section("Pattern 3: Expected tool calls")

    tool_check_local = LocalEvaluator(
        tool_calls_present,
        tool_call_args_match,
    )

    results = await evaluate_agent(
        agent=agent,
        queries=[
            "Use the get_risk_assessment tool with moderate risk level to show me options",
            "Use the calculate_returns tool for $10,000 at 7% annual rate over 10 years",
        ],
        expected_tool_calls=[
            [ExpectedToolCall("get_risk_assessment", {"risk_level": "moderate"})],
            [ExpectedToolCall("calculate_returns")],
        ],
        evaluators=tool_check_local,
    )

    for r in results:
        print(f"Provider: {r.provider}")
        print(f"Results: {r.passed}/{r.total} passed")
        for item in r.items:
            status = "PASS" if item.is_passed else "FAIL"
            print(f"  [{status}] Item {item.item_id}:")
            for score in item.scores:
                print(f"    {score.name}: {'pass' if score.passed else 'fail'}")
                if score.sample and score.sample.get("reason"):
                    print(f"      Reason: {score.sample['reason']}")

    # =========================================================================
    # Combined: All checks together + raise_for_status for CI
    # =========================================================================
    print_section("Combined: All checks (CI-friendly)")

    combined = LocalEvaluator(
        keyword_check("risk"),
        response_not_empty,
        no_specific_stock_tips,
    )

    results = await evaluate_agent(
        agent=agent,
        queries=["Tell me about risk management in investing"],
        evaluators=combined,
    )

    for r in results:
        print(f"Results: {r.passed}/{r.total} passed")
        if r.all_passed:
            print("[PASS] All combined checks passed — safe for CI")
        else:
            print("[FAIL] Some checks failed")

    # Demonstrate raise_for_status() for CI pipelines
    try:
        for r in results:
            r.raise_for_status()
        print("raise_for_status() did not raise — evaluation passed!")
    except Exception as e:
        print(f"raise_for_status() raised: {e}")


if __name__ == "__main__":
    asyncio.run(main())
