# Copyright (c) MAFEvaluations project. All rights reserved.

"""Ground-truth similarity evaluation with FoundryEvals.SIMILARITY.

Demonstrates the regression-style evaluation pattern: each test case carries
an ``expected_output`` (the canonical answer for that query) and the
``SIMILARITY`` evaluator scores how close the live agent response is to it.

Two scenarios:
1. Free-form quality answers (e.g. "Explain X in two sentences").
2. Tool-grounded factual answers where the expected text is derived from the
   underlying mock data (portfolio summaries) — the agent must paraphrase the
   tool output without losing key facts (client ID, holdings, totals).

Run:
    python evaluations/09_similarity_eval/run_similarity_eval.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import evaluate_agent
from agent_framework.foundry import FoundryEvals

from src.agents import create_financial_advisor
from src.utils import create_chat_client


def print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


# Test set: each (query, expected_output) is a regression assertion.
TEST_CASES: list[tuple[str, str]] = [
    (
        "In one sentence, what is risk tolerance?",
        "Risk tolerance is an investor's ability and willingness to endure "
        "fluctuations in the value of their investments in pursuit of higher returns.",
    ),
    (
        "Explain dollar-cost averaging in two sentences.",
        "Dollar-cost averaging is the practice of investing a fixed amount of money "
        "at regular intervals regardless of price. It reduces the impact of volatility "
        "by spreading purchases over time so you buy more shares when prices are low "
        "and fewer when they are high.",
    ),
    (
        "Show me the portfolio summary for client C001.",
        "Client C001 has a portfolio worth approximately 250,000 USD with a moderate "
        "risk profile. Holdings include diversified ETFs, blue-chip equities, and "
        "fixed income, with positions in VOO, AAPL, MSFT, and BND.",
    ),
]


async def main() -> None:
    client = create_chat_client()
    agent = create_financial_advisor(client)

    queries = [q for q, _ in TEST_CASES]
    expected = [e for _, e in TEST_CASES]

    evals = FoundryEvals(
        client=client,
        evaluators=[FoundryEvals.SIMILARITY, FoundryEvals.RELEVANCE],
    )

    print_section("Ground-truth similarity evaluation")
    results = await evaluate_agent(
        agent=agent,
        queries=queries,
        expected_output=expected,
        evaluators=evals,
        eval_name="MAFEvaluations - Similarity Demo",
    )

    for r in results:
        print(f"\nProvider: {r.provider}")
        print(f"Status:   {r.status}")
        print(f"Result:   {r.passed}/{r.total} items passed")
        if r.report_url:
            print(f"Portal:   {r.report_url}")

        for item in r.items:
            print(f"\n  Item {item.item_id}:")
            for score in item.scores:
                outcome = "PASS" if score.passed else "FAIL"
                score_value = f"{score.score:.2f}" if score.score is not None else "N/A"
                print(f"    [{outcome}] {score.name}: score={score_value}")
                if score.sample and score.sample.get("reason"):
                    reason = score.sample["reason"]
                    print(f"          reason: {reason[:160]}{'...' if len(reason) > 160 else ''}")


if __name__ == "__main__":
    asyncio.run(main())
