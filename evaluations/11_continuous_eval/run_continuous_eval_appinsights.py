# Copyright (c) MAFEvaluations project. All rights reserved.

"""Continuous evaluation streaming traces to Azure Application Insights.

This is the Application-Insights-backed variant of
``run_continuous_eval.py``. Same building blocks (configure_otel_providers +
sampled evaluate_agent), but instead of attaching only an in-memory exporter,
we also wire ``AzureMonitorTraceExporter`` so every span emitted by the
agent framework flows straight into App Insights.

End-to-end picture:
1. ``configure_otel_providers`` registers BOTH exporters — an in-memory one
   (so the demo can still print local counts) and the Azure Monitor one
   (so spans land in App Insights for production-grade observability).
2. The agent serves simulated production traffic; each call auto-instruments
   ``invoke_agent`` / ``chat`` / tool spans with token usage attributes.
3. A sample of that traffic is fed through ``evaluate_agent``.
4. We force-flush the trace provider before exit so spans actually leave the
   process before the script terminates.

Where to look in the Azure portal afterwards:
- Application Insights → Investigate → Transaction search
- Filter by Cloud role name = ``MAFEvaluations`` (set via OTEL_SERVICE_NAME below)
- Or write a KQL query like:
    dependencies
    | where cloud_RoleName == "MAFEvaluations"
    | order by timestamp desc

Configuration:
- Set APPLICATIONINSIGHTS_CONNECTION_STRING in .env (full connection string,
  including InstrumentationKey, IngestionEndpoint, etc.).

Run:
    python evaluations/11_continuous_eval/run_continuous_eval_appinsights.py
"""

import asyncio
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Cloud role name shows up in App Insights as the service identity. Set this
# BEFORE configure_otel_providers so it gets attached to the resource.
os.environ.setdefault("OTEL_SERVICE_NAME", "MAFEvaluations")

from agent_framework import (  # noqa: E402
    LocalEvaluator,
    evaluate_agent,
    keyword_check,
)
from agent_framework.observability import configure_otel_providers  # noqa: E402
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from opentelemetry import trace  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # noqa: E402

from src.agents import create_financial_advisor  # noqa: E402
from src.utils import create_chat_client  # noqa: E402

load_dotenv()


def print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


PRODUCTION_TRAFFIC = [
    "What is dollar-cost averaging?",
    "Explain the difference between stocks and bonds.",
    "Show me the portfolio summary for client C001.",
    "Should I invest in cryptocurrency right now?",
    "Calculate returns on $5,000 at 6% over 15 years.",
]


async def main() -> None:
    connection_string = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        print("Error: APPLICATIONINSIGHTS_CONNECTION_STRING is not set in .env.")
        print("Add the full connection string (InstrumentationKey=...;IngestionEndpoint=...) to .env.")
        sys.exit(1)

    # Step 1 — set up OpenTelemetry with TWO exporters:
    # one in-memory for local visibility during the demo,
    # one Azure Monitor for the production-grade pipeline.
    mem_exporter = InMemorySpanExporter()
    azure_exporter = AzureMonitorTraceExporter(connection_string=connection_string)
    configure_otel_providers(
        enable_sensitive_data=False,
        exporters=[mem_exporter, azure_exporter],
    )

    client = create_chat_client()
    agent = create_financial_advisor(client)

    # Step 2 — serve "production traffic". Every call is auto-instrumented
    # and replicated to both exporters.
    print_section("Step 1: Serve production traffic (streaming to App Insights)")
    for query in PRODUCTION_TRAFFIC:
        response = await agent.run(query)
        print(f"  -> {query[:60]:<62}  ({len(response.text)} chars)")

    # Step 3 — local summary using the in-memory exporter copy.
    spans = mem_exporter.get_finished_spans()
    print_section(f"Step 2: Telemetry summary ({len(spans)} spans captured locally)")
    span_kinds = Counter(s.name for s in spans)
    for name, count in span_kinds.most_common():
        print(f"  {count:>4}  {name}")

    total_in = 0
    total_out = 0
    for s in spans:
        attrs = s.attributes or {}
        total_in += int(attrs.get("gen_ai.usage.input_tokens", 0) or 0)
        total_out += int(attrs.get("gen_ai.usage.output_tokens", 0) or 0)
    if total_in or total_out:
        print(f"\n  Tokens used:  input={total_in}  output={total_out}")

    # Step 4 — sample N items from the traffic and run evaluators.
    print_section("Step 3: Run continuous evaluators over sampled traffic")
    evaluators = LocalEvaluator(
        keyword_check("disclaimer"),
        keyword_check("not personalized"),
    )
    results = await evaluate_agent(
        agent=agent,
        queries=PRODUCTION_TRAFFIC,
        evaluators=evaluators,
        eval_name="MAFEvaluations - Continuous Eval (App Insights)",
    )

    for r in results:
        print(f"\n  Provider: {r.provider}")
        print(f"  Result:   {r.passed}/{r.total} items passed")
        for check_name, counts in r.per_evaluator.items():
            status = "PASS" if counts["failed"] == 0 else "FAIL"
            print(f"    [{status}] {check_name}: passed={counts['passed']}  failed={counts['failed']}")

    # Step 5 — flush spans so they actually leave the process before exit.
    print_section("Step 4: Flushing spans to Application Insights")
    tracer_provider = trace.get_tracer_provider()
    if hasattr(tracer_provider, "force_flush"):
        flushed = tracer_provider.force_flush(timeout_millis=10000)
        print(f"  Force flush completed (success={flushed}).")
    print("  Spans typically appear in the portal within 1-3 minutes.")
    print("  Look in Application Insights → Transaction search,")
    print("  filtering by Cloud role name 'MAFEvaluations'.")
    print()
    print("  Suggested KQL query (paste into Logs blade):")
    print("    dependencies")
    print("    | where cloud_RoleName == 'MAFEvaluations'")
    print("    | order by timestamp desc")


if __name__ == "__main__":
    asyncio.run(main())
