# Copyright (c) MAFEvaluations project. All rights reserved.

"""Evaluate multi-turn conversations with different split strategies.

The same conversation can be evaluated three ways:
1. LAST_TURN — "Was the last response good given context?"
2. FULL — "Did the whole conversation serve the original request?"
3. per_turn_items — "Was each individual response appropriate?"

Prerequisites:
- Azure AI Foundry project with a deployed model
- Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL in .env

Run:
    python evaluations/02_foundry_eval/run_multiturn_eval.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import Content, ConversationSplit, EvalItem, FunctionTool, Message
from agent_framework.foundry import FoundryEvals

from src.utils import create_chat_client


# A multi-turn financial advisor conversation with tool calls.
CONVERSATION: list[Message] = [
    # Turn 1: user asks about risk assessment → agent calls tool → responds
    Message("user", ["What investment strategy works for moderate risk tolerance?"]),
    Message(
        "assistant",
        [Content.from_function_call("c1", "get_risk_assessment", arguments={"risk_level": "moderate"})],
    ),
    Message(
        "tool",
        [Content.from_function_result(
            "c1",
            result='{"risk_assessment": {"risk_level": "Moderate", "recommended_allocation": {"large_cap_stocks": "40%", "bonds": "25%", "international": "20%", "cash": "15%"}, "expected_annual_return": "6-9%"}}',
        )],
    ),
    Message("assistant", [
        "For moderate risk tolerance, I'd recommend a balanced allocation: 40% large-cap stocks, "
        "25% bonds, 20% international, and 15% cash. This targets 6-9% annual returns. "
        "Please consult a licensed financial advisor for personalized advice."
    ]),
    # Turn 2: user asks about projected returns → agent calls tool → responds
    Message("user", ["What would $50,000 grow to over 15 years at 7%?"]),
    Message(
        "assistant",
        [Content.from_function_call("c2", "calculate_returns", arguments={"principal": 50000, "annual_rate": 0.07, "years": 15})],
    ),
    Message(
        "tool",
        [Content.from_function_result(
            "c2",
            result='{"calculation": {"principal": "$50,000.00", "projected_value": "$137,951.93", "total_return": "$87,951.93", "total_return_pct": "175.9%"}}',
        )],
    ),
    Message("assistant", [
        "At 7% annual return, $50,000 would grow to approximately $137,952 over 15 years — "
        "a total return of about 176%. Remember, past performance doesn't guarantee future results."
    ]),
    # Turn 3: user asks a follow-up comparison
    Message("user", ["How does that compare to a conservative strategy?"]),
    Message("assistant", [
        "A conservative strategy targets 4-6% annual returns. At 5%, the same $50,000 would grow to "
        "about $103,946 over 15 years — roughly $34,000 less than the moderate 7% scenario. "
        "The trade-off is lower volatility and smaller potential drawdowns. "
        "This is general information — please consult a licensed advisor for your specific situation."
    ]),
]

TOOLS = [
    FunctionTool(name="get_risk_assessment", description="Get risk assessment for an investment strategy."),
    FunctionTool(name="calculate_returns", description="Calculate projected investment returns."),
]


def print_split(item: EvalItem, split: ConversationSplit = ConversationSplit.LAST_TURN) -> None:
    query_msgs, response_msgs = item.split_messages(split)
    print(f"  query_messages ({len(query_msgs)}):")
    for m in query_msgs:
        text = m.text or ""
        print(f"    {m.role}: {text[:70]}")
    print(f"  response_messages ({len(response_msgs)}):")
    for m in response_msgs:
        text = m.text or ""
        print(f"    {m.role}: {text[:70]}")


async def main() -> None:
    client = create_chat_client(provider="foundry")

    # =========================================================================
    # Strategy 1: LAST_TURN (default)
    # =========================================================================
    print("=" * 70)
    print("Strategy 1: LAST_TURN — evaluate the final response")
    print("=" * 70)

    item = EvalItem(CONVERSATION, tools=TOOLS)
    print_split(item, ConversationSplit.LAST_TURN)

    results = await FoundryEvals(
        client=client,
        evaluators=[FoundryEvals.RELEVANCE, FoundryEvals.COHERENCE],
    ).evaluate([item], eval_name="Financial Advisor: LAST_TURN")

    print(f"\n  Result: {results.passed}/{results.total} passed")
    if results.report_url:
        print(f"  Portal: {results.report_url}")
    for ir in results.items:
        for s in ir.scores:
            print(f"    {'PASS' if s.passed else 'FAIL'} {s.name}: {s.score}")
    print()

    # =========================================================================
    # Strategy 2: FULL
    # =========================================================================
    print("=" * 70)
    print("Strategy 2: FULL — evaluate the entire conversation trajectory")
    print("=" * 70)

    print_split(item, ConversationSplit.FULL)

    results = await FoundryEvals(
        client=client,
        evaluators=[FoundryEvals.RELEVANCE, FoundryEvals.COHERENCE],
        conversation_split=ConversationSplit.FULL,
    ).evaluate([item], eval_name="Financial Advisor: FULL")

    print(f"\n  Result: {results.passed}/{results.total} passed")
    if results.report_url:
        print(f"  Portal: {results.report_url}")
    for ir in results.items:
        for s in ir.scores:
            print(f"    {'PASS' if s.passed else 'FAIL'} {s.name}: {s.score}")
    print()

    # =========================================================================
    # Strategy 3: per_turn_items
    # =========================================================================
    print("=" * 70)
    print("Strategy 3: per_turn_items — evaluate each turn independently")
    print("=" * 70)

    items = EvalItem.per_turn_items(CONVERSATION, tools=TOOLS)
    print(f"  Split into {len(items)} items from {len(CONVERSATION)} messages:\n")
    for i, it in enumerate(items):
        print(f"  Turn {i + 1}: query={it.query[:60]!r}... response={it.response[:50]!r}...")
    print()

    results = await FoundryEvals(
        client=client,
        evaluators=[FoundryEvals.RELEVANCE, FoundryEvals.COHERENCE],
    ).evaluate(items, eval_name="Financial Advisor: Per-Turn")

    print(f"\n  Result: {results.passed}/{results.total} passed ({len(items)} items × 2 evaluators)")
    if results.report_url:
        print(f"  Portal: {results.report_url}")
    for ir in results.items:
        for s in ir.scores:
            print(f"    {'PASS' if s.passed else 'FAIL'} {s.name}: {s.score}")
    print()

    print("=" * 70)
    print("All strategies complete. Compare results in the Foundry portal.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
