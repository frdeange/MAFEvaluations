# Copyright (c) MAFEvaluations project. All rights reserved.

"""Evaluate a Foundry-deployed agent or model with evaluate_foundry_target.

This is the CI/CD-friendly evaluation flavour: instead of running the agent
client-side, you point Foundry at a registered target (an Azure AI Agent or
a model deployment) and Foundry both invokes it and runs the evaluators on
the captured outputs. Returns a portal URL with everything pre-rendered.

Use this when:
- You want to evaluate an agent that is already deployed in Foundry.
- You want a quality gate inside a CI/CD pipeline that does not embed the
  agent code (e.g. a release gate after deploying a new agent version).
- You want the eval results auto-archived in the Foundry portal alongside
  the deployment.

This demo is **conditional**:
- If the env var ``FOUNDRY_TARGET_AGENT_NAME`` is set, runs end-to-end
  against that registered agent.
- Otherwise it explains what to set and prints the code that would run, so
  the demo doubles as living documentation for the API.

Run:
    python evaluations/12_foundry_target_eval/run_foundry_target_eval.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework.foundry import FoundryEvals, evaluate_foundry_target

from src.utils import create_chat_client


TEST_QUERIES = [
    "What is risk tolerance?",
    "Should I invest all my savings in a single tech stock?",
    "Explain dollar-cost averaging in two sentences.",
]

EVALUATORS = [
    FoundryEvals.RELEVANCE,
    FoundryEvals.GROUNDEDNESS,
    FoundryEvals.TASK_ADHERENCE,
]


def print_section(title: str) -> None:
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def _print_explanation(target_name_var: str = "FOUNDRY_TARGET_AGENT_NAME") -> None:
    print_section("Demo A — evaluate_foundry_target (documentation mode)")
    print(
        "This demo evaluates a Foundry-registered agent or model deployment.\n"
        "Foundry invokes the target itself, captures the outputs, and runs the\n"
        "selected evaluators on them. The result is a portal URL.\n\n"
        f"To run it end-to-end set:\n"
        f"  {target_name_var} = <name of an Azure AI Agent registered in your Foundry project>\n\n"
        "  (you can also adjust FOUNDRY_TARGET_TYPE if your target is a model\n"
        "   deployment rather than an agent — defaults to 'azure_ai_agent')\n\n"
        "Equivalent code:\n"
    )
    snippet = (
        '    from agent_framework.foundry import FoundryEvals, evaluate_foundry_target\n'
        '    from src.utils import create_chat_client\n\n'
        '    client = create_chat_client()\n'
        '    results = await evaluate_foundry_target(\n'
        '        target={"type": "azure_ai_agent", "name": "<your-agent-name>"},\n'
        '        test_queries=[\n'
        '            "What is risk tolerance?",\n'
        '            "Explain dollar-cost averaging in two sentences.",\n'
        '        ],\n'
        '        evaluators=[FoundryEvals.RELEVANCE, FoundryEvals.TASK_ADHERENCE],\n'
        '        client=client,\n'
        '        model=os.environ["FOUNDRY_MODEL"],\n'
        '    )\n'
        '    print("Portal:", results.report_url)\n'
    )
    print(snippet)
    print(
        "Why use this instead of evaluate_agent()?\n"
        "  - The agent code stays inside Foundry — your pipeline never imports it.\n"
        "  - Foundry runs the evaluators server-side and archives the results.\n"
        "  - Same evaluator catalog as FoundryEvals, including safety scorers.\n"
    )


async def main() -> None:
    target_name = os.environ.get("FOUNDRY_TARGET_AGENT_NAME")
    target_type = os.environ.get("FOUNDRY_TARGET_TYPE", "azure_ai_agent")
    model = os.environ.get("FOUNDRY_MODEL")

    if not target_name:
        _print_explanation()
        return

    if not model:
        print("ERROR: FOUNDRY_MODEL must be set to the judge LLM deployment name.")
        sys.exit(1)

    client = create_chat_client(provider="foundry")

    print_section(
        f"Demo A — evaluate_foundry_target ({target_type} = {target_name!r})"
    )
    print(f"Evaluators: {', '.join(EVALUATORS)}")
    print(f"Test queries: {len(TEST_QUERIES)}")

    results = await evaluate_foundry_target(
        target={"type": target_type, "name": target_name},
        test_queries=TEST_QUERIES,
        evaluators=EVALUATORS,
        client=client,
        model=model,
        eval_name="MAFEvaluations - Foundry Target Demo",
    )

    print(f"\nStatus:  {results.status}")
    print(f"Result:  {results.passed}/{results.total} items passed")
    if results.report_url:
        print(f"Portal:  {results.report_url}")


if __name__ == "__main__":
    asyncio.run(main())
