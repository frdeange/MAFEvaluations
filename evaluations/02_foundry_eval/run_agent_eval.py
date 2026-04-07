# Copyright (c) MAFEvaluations project. All rights reserved.

"""Evaluate a Financial Advisor agent using Azure AI Foundry's built-in evaluators.

Demonstrates two patterns:
1. evaluate_agent(responses=...) — evaluate a response you already have
2. evaluate_agent(queries=...) — run + evaluate in one call, with optional ConversationSplit

Prerequisites:
- Azure AI Foundry project with a deployed model
- Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL in .env

Run:
    python evaluations/02_foundry_eval/run_agent_eval.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import ConversationSplit, evaluate_agent
from agent_framework.foundry import FoundryEvals

from src.agents import create_financial_advisor
from src.utils import create_chat_client


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


async def main() -> None:
    client = create_chat_client(provider="foundry")
    agent = create_financial_advisor(client)
    evals = FoundryEvals(client=client)

    # =========================================================================
    # Pattern 1: evaluate_agent(responses=...) — evaluate existing response
    # =========================================================================
    print_section("Pattern 1: Evaluate existing response")

    query = "What investment options are available for moderate risk tolerance?"
    response = await agent.run(query)
    print(f"Agent said: {response.text[:150]}...")

    results = await evaluate_agent(
        agent=agent,
        responses=response,
        queries=[query],
        evaluators=FoundryEvals(
            client=client,
            evaluators=[FoundryEvals.RELEVANCE, FoundryEvals.TOOL_CALL_ACCURACY],
        ),
    )

    for r in results:
        print(f"Status: {r.status}")
        print(f"Results: {r.passed}/{r.total} passed")
        if r.report_url:
            print(f"Portal: {r.report_url}")
        if r.all_passed:
            print("[PASS] All evaluators passed")
        else:
            print(f"[FAIL] {r.failed} failed")

    # =========================================================================
    # Pattern 2a: evaluate_agent(queries=...) — run + evaluate batch
    # =========================================================================
    print_section("Pattern 2a: Run + evaluate batch queries")

    results = await evaluate_agent(
        agent=agent,
        queries=[
            "What's a good strategy for a conservative investor near retirement?",
            "Show me the current market data for the S&P 500",
            "Calculate projected returns for $50,000 at 8% over 20 years",
        ],
        evaluators=evals,  # uses smart defaults (auto-adds tool_call_accuracy)
    )

    for r in results:
        print(f"Status: {r.status}")
        print(f"Results: {r.passed}/{r.total} passed")
        if r.report_url:
            print(f"Portal: {r.report_url}")
        if r.all_passed:
            print("[PASS] All passed")
        else:
            print(f"[FAIL] {r.failed} failed")

    # =========================================================================
    # Pattern 2b: evaluate_agent() with ConversationSplit.FULL
    # =========================================================================
    print_section("Pattern 2b: With ConversationSplit.FULL")

    results = await evaluate_agent(
        agent=agent,
        queries=[
            "I'm 35 years old and want to invest $100,000. What should I consider?",
        ],
        evaluators=evals,
        conversation_split=ConversationSplit.FULL,
    )

    for r in results:
        print(f"Status: {r.status}")
        print(f"Results: {r.passed}/{r.total} passed")
        if r.report_url:
            print(f"Portal: {r.report_url}")
        if r.all_passed:
            print("[PASS] Full conversation evaluation passed")
        else:
            print(f"[FAIL] {r.failed} failed")


if __name__ == "__main__":
    asyncio.run(main())
