# Copyright (c) MAFEvaluations project. All rights reserved.

"""Run the GAIA benchmark with a Financial Advisor agent.

GAIA (General AI Assistant) evaluates agents on general assistant tasks
with real-world questions that require reasoning and tool use.

Prerequisites:
- pip install "agent-framework-lab[gaia]"
- Set HF_TOKEN environment variable (access to gaia-benchmark/GAIA dataset)
- Set FOUNDRY_PROJECT_ENDPOINT or OPENAI_API_KEY in .env

Run:
    python evaluations/07_benchmarks/run_gaia.py
    python evaluations/07_benchmarks/run_gaia.py --level 1 --max-n 5
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework.lab.gaia import GAIA, Evaluation, GAIATelemetryConfig, Prediction, Task
from dotenv import load_dotenv

from src.agents import create_financial_advisor
from src.utils import create_chat_client

load_dotenv()


async def evaluate_task(task: Task, prediction: Prediction) -> Evaluation:
    """Evaluate whether the prediction contains the correct answer."""
    is_correct = (task.answer or "").lower() in prediction.prediction.lower()
    return Evaluation(is_correct=is_correct, score=1 if is_correct else 0)


async def main(level: int = 1, max_n: int = 3, result_file: str | None = None) -> None:
    print("=" * 60)
    print("  GAIA Benchmark — Financial Advisor Agent")
    print("=" * 60)

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("\nError: HF_TOKEN environment variable not set.")
        print("Get a token at: https://huggingface.co/settings/tokens")
        print("Request dataset access: https://huggingface.co/datasets/gaia-benchmark/GAIA")
        return

    client = create_chat_client()
    agent = create_financial_advisor(client)

    print(f"\nLevel: {level}")
    print(f"Max tasks: {max_n}")
    if result_file:
        print(f"Results file: {result_file}")

    telemetry_config = GAIATelemetryConfig(
        enable_tracing=True,
        trace_to_file=result_file is not None,
        file_path=result_file,
    )

    async def run_task(task: Task) -> Prediction:
        """Run a single GAIA task using the financial advisor agent."""
        input_message = f"Task: {task.question}"
        if task.file_name:
            input_message += f"\nFile: {task.file_name}"
        result = await agent.run(input_message)
        return Prediction(prediction=result.text, messages=result.messages)

    runner = GAIA(
        evaluator=evaluate_task,
        telemetry_config=telemetry_config,
    )

    results = await runner.run(
        run_task,
        level=level,
        max_n=max_n,
        parallel=1,
        timeout=120,
        out=result_file,
    )

    # Summary
    total = len(results)
    correct = sum(1 for r in results if r.evaluation.is_correct)
    accuracy = correct / total if total > 0 else 0.0
    avg_runtime = sum(r.runtime_seconds or 0 for r in results) / total if total > 0 else 0.0

    print(f"\n{'=' * 60}")
    print("GAIA Benchmark Summary")
    print(f"{'=' * 60}")
    print(f"Total: {total}, Correct: {correct}, Accuracy: {accuracy:.3f}")
    print(f"Average runtime: {avg_runtime:.2f}s")
    if result_file:
        print(f"Results saved to: {result_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run GAIA benchmark")
    parser.add_argument("--level", type=int, default=1, choices=[1, 2, 3])
    parser.add_argument("--max-n", type=int, default=3)
    parser.add_argument("--result-file", type=str, default=None)
    args = parser.parse_args()

    asyncio.run(main(level=args.level, max_n=args.max_n, result_file=args.result_file))
