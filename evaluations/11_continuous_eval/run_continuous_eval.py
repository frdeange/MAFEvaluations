# Copyright (c) MAFEvaluations project. All rights reserved.

"""Continuous evaluation with OpenTelemetry instrumentation.

The "deploy → forget" anti-pattern. In production you want to:
1. Run the agent under live traffic with full OpenTelemetry traces.
2. Pipe a configurable sample of those interactions through evaluators.
3. Track quality drift over time.

This demo shows the building blocks the Microsoft Agent Framework gives you
for that loop:

- ``configure_otel_providers`` enables the standard OTel SDK and wires the
  framework's auto-instrumentation. We attach an in-memory span exporter so
  the demo can show the captured spans inline. In production you would point
  this at OTLP / Application Insights / Jaeger.
- ``evaluate_agent`` then runs over a sampled subset of the traffic.

The combination = continuous quality monitoring without spinning up a
separate eval pipeline.

Run:
    python evaluations/11_continuous_eval/run_continuous_eval.py
"""

import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import (
    LocalEvaluator,
    evaluate_agent,
    keyword_check,
)
from agent_framework.observability import configure_otel_providers
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.agents import create_financial_advisor
from src.utils import create_chat_client


def print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


# Simulate live production traffic — these would come from your real users.
PRODUCTION_TRAFFIC = [
    "What is dollar-cost averaging?",
    "Explain the difference between stocks and bonds.",
    "Show me the portfolio summary for client C001.",
    "Should I invest in cryptocurrency right now?",
    "Calculate returns on $5,000 at 6% over 15 years.",
]


async def main() -> None:
    # Step 1 — set up OpenTelemetry. In-memory exporter for the demo;
    # in production swap for OTLPSpanExporter -> App Insights / Jaeger / etc.
    span_exporter = InMemorySpanExporter()
    configure_otel_providers(
        enable_sensitive_data=False,
        exporters=[span_exporter],
    )

    client = create_chat_client()
    agent = create_financial_advisor(client)

    # Step 2 — serve "production traffic". Every call is auto-instrumented.
    print_section("Step 1: Serve production traffic (with OTel traces)")
    for query in PRODUCTION_TRAFFIC:
        response = await agent.run(query)
        print(f"  -> {query[:60]:<62}  ({len(response.text)} chars)")

    # Step 3 — inspect captured spans.
    spans = span_exporter.get_finished_spans()
    print_section(f"Step 2: Telemetry summary ({len(spans)} spans captured)")
    span_kinds = Counter(s.name for s in spans)
    for name, count in span_kinds.most_common():
        print(f"  {count:>4}  {name}")

    # Token usage rollup (when available on the spans)
    total_in = 0
    total_out = 0
    for s in spans:
        attrs = s.attributes or {}
        total_in += int(attrs.get("gen_ai.usage.input_tokens", 0) or 0)
        total_out += int(attrs.get("gen_ai.usage.output_tokens", 0) or 0)
    if total_in or total_out:
        print(f"\n  Tokens used:  input={total_in}  output={total_out}")

    # Step 4 — sample N items from the traffic and run evaluators.
    # In real life you would store traffic and sample 1-5%; here we eval all 5.
    print_section("Step 3: Run continuous evaluators over sampled traffic")
    evaluators = LocalEvaluator(
        keyword_check("disclaimer"),
        keyword_check("not personalized"),
    )
    results = await evaluate_agent(
        agent=agent,
        queries=PRODUCTION_TRAFFIC,
        evaluators=evaluators,
        eval_name="MAFEvaluations - Continuous Eval",
    )

    for r in results:
        print(f"\n  Provider: {r.provider}")
        print(f"  Result:   {r.passed}/{r.total} items passed")
        for check_name, counts in r.per_evaluator.items():
            status = "PASS" if counts["failed"] == 0 else "FAIL"
            print(f"    [{status}] {check_name}: passed={counts['passed']}  failed={counts['failed']}")

    print_section("Step 4: Production wiring tips")
    print("  - Replace InMemorySpanExporter with OTLPSpanExporter")
    print("    pointing at Application Insights / Jaeger / Grafana Tempo.")
    print("  - Sample a small percentage of production traffic (1-5%) for")
    print("    continuous evaluation; full eval is too expensive.")
    print("  - Schedule evaluate_agent runs (e.g. nightly) and alert on")
    print("    score drops > 10% to catch quality regressions.")


if __name__ == "__main__":
    asyncio.run(main())
