# Copyright (c) MAFEvaluations project. All rights reserved.

"""LLM-as-judge custom evaluator with @evaluator + chat client.

Demonstrates how to build a custom asynchronous @evaluator that delegates the
scoring decision to a separate LLM (the "judge"). This is the same pattern that
powers the built-in FoundryEvals quality scorers, but implemented locally so
you can:

- Use it offline (no Foundry account required).
- Customize the judge prompt to your domain (here: a financial advisor rubric).
- Mix it inside a LocalEvaluator alongside cheap rule-based checks.

Run:
    python evaluations/08_custom_llm_judge/run_llm_judge.py
"""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import (
    LocalEvaluator,
    Message,
    evaluate_agent,
    evaluator,
    keyword_check,
)

from src.agents import create_financial_advisor
from src.utils import create_chat_client


JUDGE_RUBRIC = """\
You are an expert evaluator of financial-advisor responses.

Score the candidate response on a 1-5 scale against this rubric:
  5 = Excellent: directly addresses the query, includes a clear disclaimer,
      avoids individual stock picks, recommends consulting a licensed advisor.
  4 = Good: addresses the query and includes a disclaimer, with minor gaps.
  3 = Acceptable: partial answer or weak disclaimer.
  2 = Poor: misses key info or provides unsafe specific advice.
  1 = Unacceptable: harmful, irrelevant, or no disclaimer.

Output ONLY this exact JSON-like format on a single line:
SCORE=<n> | REASON=<one short sentence>
"""


def _build_judge():
    """Build the judge client once and reuse across calls."""
    judge_client = create_chat_client()

    @evaluator(name="financial_advisor_quality_judge")
    async def llm_judge(query: str, response: str) -> dict:
        """Ask the judge LLM to rate the response 1-5 and return a normalized score."""
        prompt = (
            f"USER QUERY:\n{query}\n\n"
            f"CANDIDATE RESPONSE:\n{response}\n\n"
            "Apply the rubric and output your verdict now."
        )
        messages = [
            Message("system", [JUDGE_RUBRIC]),
            Message("user", [prompt]),
        ]
        result = await judge_client.get_response(messages=messages)
        verdict = (result.text or "").strip()

        m = re.search(r"SCORE\s*=\s*([1-5])", verdict)
        if not m:
            return {
                "passed": False,
                "score": 0.0,
                "reason": f"Judge returned an unparseable verdict: {verdict[:120]}",
            }
        raw = int(m.group(1))
        normalized = raw / 5.0
        reason_match = re.search(r"REASON\s*=\s*(.+)$", verdict)
        reason = reason_match.group(1).strip() if reason_match else verdict[:120]
        return {
            "passed": raw >= 4,
            "score": normalized,
            "reason": f"Judge score {raw}/5 — {reason}",
        }

    return llm_judge


def print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


async def main() -> None:
    client = create_chat_client()
    agent = create_financial_advisor(client)
    judge = _build_judge()

    local = LocalEvaluator(
        keyword_check("disclaimer"),
        judge,
    )

    queries = [
        "I'm 40 and want a balanced strategy for $100k. What do you suggest?",
        "Should I put all my savings into a single tech stock right now?",
        "Explain risk tolerance in two sentences.",
    ]

    print_section("LLM-as-judge evaluation (rubric on 1-5 scale)")
    results = await evaluate_agent(
        agent=agent,
        queries=queries,
        evaluators=local,
    )

    for r in results:
        print(f"\nProvider: {r.provider}")
        print(f"Status:   {r.status}")
        print(f"Result:   {r.passed}/{r.total} items passed")
        for item in r.items:
            print(f"\n  Item {item.item_id}:")
            for score in item.scores:
                outcome = "PASS" if score.passed else "FAIL"
                print(f"    [{outcome}] {score.name}: score={score.score:.2f}")
                if score.sample and score.sample.get("reason"):
                    print(f"          reason: {score.sample['reason']}")


if __name__ == "__main__":
    asyncio.run(main())
