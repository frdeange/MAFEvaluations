# Copyright (c) MAFEvaluations project. All rights reserved.

"""Evaluate tool-calling accuracy of the Financial Advisor agent.

Uses AgentEvalConverter to manually convert agent responses into EvalItems,
then evaluates with FoundryEvals.TOOL_CALL_ACCURACY.

Prerequisites:
- Azure AI Foundry project with a deployed model
- Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL in .env

Run:
    python evaluations/02_foundry_eval/run_tool_calls_eval.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import AgentEvalConverter
from agent_framework.foundry import FoundryEvals

from src.agents import create_financial_advisor
from src.utils import create_chat_client


async def main() -> None:
    client = create_chat_client(provider="foundry")
    agent = create_financial_advisor(client)

    queries = [
        "Show me client C001's portfolio summary",
        "What's the current price of QQQ?",
        "Calculate returns for $25,000 at 6% for 15 years",
        "What investment options are available in the ETF category?",
        "What's the recommended allocation for aggressive risk tolerance?",
    ]

    # Run agent and convert each response to an eval item
    items = []
    for q in queries:
        response = await agent.run(q)
        print(f"Query: {q}")
        print(f"Response: {response.text[:120]}...")

        item = AgentEvalConverter.to_eval_item(query=q, response=response, agent=agent)
        items.append(item)

        print(f"  Has tools: {item.tools is not None}")
        if item.tools:
            print(f"  Tools defined: {[t.name for t in item.tools]}")
        print()

    # Submit to Foundry with tool-related evaluators
    evals = FoundryEvals(
        client=client,
        evaluators=[
            FoundryEvals.RELEVANCE,
            FoundryEvals.TOOL_CALL_ACCURACY,
        ],
    )
    results = await evals.evaluate(items, eval_name="Financial Advisor Tool Call Eval")

    print(f"\nStatus: {results.status}")
    print(f"Results: {results.passed}/{results.total} passed")
    if results.report_url:
        print(f"Portal: {results.report_url}")

    # Per-item details
    for item_result in results.items:
        print(f"\n  Item {item_result.item_id}: {item_result.status}")
        if item_result.input_text:
            print(f"    Query: {item_result.input_text[:80]}...")
        for score in item_result.scores:
            status = "PASS" if score.passed else "FAIL"
            print(f"    [{status}] {score.name}: {score.score}")


if __name__ == "__main__":
    asyncio.run(main())
