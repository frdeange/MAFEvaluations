# Copyright (c) MAFEvaluations project. All rights reserved.

"""Evaluate agent responses that already exist in Foundry (zero-code-change).

Uses evaluate_traces(response_ids=...) to evaluate past agent runs by their
Responses API IDs, without re-running the agent.

Prerequisites:
- Azure AI Foundry project with a deployed model
- Response IDs from prior agent runs (store=True)
- Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL in .env

Run:
    python evaluations/02_foundry_eval/run_traces_eval.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework.foundry import FoundryEvals, evaluate_traces

from src.agents import create_financial_advisor
from src.utils import create_chat_client


async def main() -> None:
    client = create_chat_client(provider="foundry")

    # =========================================================================
    # Step 1: Run the agent with store=True to capture response IDs
    # =========================================================================
    print("=" * 60)
    print("  Step 1: Run agent and capture response IDs")
    print("=" * 60)

    # Create agent with store=True so responses are persisted
    agent = create_financial_advisor(client, store=True)

    queries = [
        "What's a good investment strategy for someone in their 40s?",
        "Show me current market data for SPY",
    ]

    response_ids = []
    for q in queries:
        response = await agent.run(q)
        # Capture the response_id from the agent response
        if hasattr(response, "response_id") and response.response_id:
            response_ids.append(response.response_id)
            print(f"Query: {q}")
            print(f"  Response ID: {response.response_id}")
            print(f"  Response: {response.text[:100]}...")
        else:
            print(f"Query: {q}")
            print("  No response_id captured (store may not be enabled)")

    if not response_ids:
        print("\nNo response IDs captured. Ensure the Foundry client supports store=True.")
        print("Skipping trace evaluation.")
        return

    # =========================================================================
    # Step 2: Evaluate the stored responses by ID
    # =========================================================================
    print(f"\n{'=' * 60}")
    print("  Step 2: Evaluate stored responses by ID")
    print(f"{'=' * 60}")

    results = await evaluate_traces(
        response_ids=response_ids,
        evaluators=[FoundryEvals.RELEVANCE, FoundryEvals.GROUNDEDNESS],
        client=client,
        model=client.model,
    )

    print(f"Status: {results.status}")
    if hasattr(results, "result_counts") and results.result_counts:
        print(f"Results: {results.result_counts}")
    if results.report_url:
        print(f"Portal: {results.report_url}")

    print("\nTrace evaluation complete.")
    print("This demonstrates zero-code-change evaluation of past agent runs.")


if __name__ == "__main__":
    asyncio.run(main())
