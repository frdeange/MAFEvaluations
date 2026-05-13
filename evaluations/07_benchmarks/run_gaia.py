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
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import agent_framework.observability as _af_obs  # noqa: E402

if not hasattr(_af_obs, "setup_observability"):
    def _setup_observability_shim(
        *,
        enable_sensitive_data: bool | None = None,
        otlp_endpoint: str | None = None,
        applicationinsights_connection_string: str | None = None,
        **_extra,
    ) -> None:
        if otlp_endpoint or applicationinsights_connection_string:
            warnings.warn(
                "agent-framework 1.3.0 no longer accepts otlp_endpoint or "
                "applicationinsights_connection_string as kwargs. "
                "Set OTEL_EXPORTER_OTLP_ENDPOINT / "
                "APPLICATIONINSIGHTS_CONNECTION_STRING env vars instead.",
                RuntimeWarning,
                stacklevel=2,
            )
        _af_obs.configure_otel_providers(enable_sensitive_data=enable_sensitive_data)

    _af_obs.setup_observability = _setup_observability_shim

# ---------------------------------------------------------------------------
# Second compatibility shim: same lab version reads metadata.jsonl but the
# HF dataset gaia-benchmark/GAIA now ships metadata.parquet (identical schema,
# just a different container). Replace the lab's loader with a parquet-aware
# version so the benchmark can find tasks again.
# ---------------------------------------------------------------------------
import agent_framework_lab_gaia.gaia as _lab_gaia  # noqa: E402


def _load_gaia_local_parquet(repo_dir, wanted_levels=None, max_n=None):  # type: ignore[no-untyped-def]
    """Parquet-aware replacement for `agent_framework_lab_gaia.gaia._load_gaia_local`."""
    import random
    from pathlib import Path

    import pandas as pd

    tasks: list = []
    repo_dir = Path(repo_dir)

    for parquet_path in repo_dir.rglob("metadata.parquet"):
        df = pd.read_parquet(parquet_path)
        for rec in df.to_dict(orient="records"):
            q = rec.get("Question") or rec.get("question")
            ans = rec.get("Final answer") or rec.get("answer")
            qid = str(rec.get("task_id") or rec.get("id") or f"{parquet_path.stem}:{len(tasks)}")
            lvl = rec.get("Level") or rec.get("level")
            try:
                lvl = int(lvl)
            except (TypeError, ValueError):
                pass
            fname = rec.get("file_name") or None
            if not q or ans is None or ans == "":
                continue
            if wanted_levels and (lvl not in wanted_levels):
                continue
            tasks.append(
                _lab_gaia.Task(
                    task_id=qid,
                    question=q,
                    answer=str(ans),
                    level=lvl,
                    file_name=fname,
                    metadata=rec,
                )
            )

    random.shuffle(tasks)
    if max_n:
        tasks = tasks[:max_n]
    return tasks


_lab_gaia._load_gaia_local = _load_gaia_local_parquet

from agent_framework.lab.gaia import GAIA, Evaluation, GAIATelemetryConfig, Prediction, Task  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from src.agents import create_financial_advisor  # noqa: E402
from src.utils import create_chat_client  # noqa: E402

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

    # Per-task breakdown — essential for understanding *why* the agent failed,
    # not just *that* it failed.
    print(f"\n{'-' * 60}")
    print("  Task-by-task breakdown")
    print(f"{'-' * 60}")
    for i, r in enumerate(results, 1):
        q = (r.task.question or "").strip()
        if len(q) > 140:
            q = q[:140] + "..."
        expected = r.task.answer or "(none)"
        got = (r.prediction.prediction or "").strip().replace("\n", " ")
        if len(got) > 240:
            got = got[:240] + "..."
        marker = "PASS" if r.evaluation.is_correct else "FAIL"
        err = getattr(r, "error", None)
        print(f"\n[{i}] [{marker}] level={r.task.level}  runtime={r.runtime_seconds:.1f}s")
        print(f"     Question: {q}")
        print(f"     Expected: {expected}")
        print(f"     Got:      {got or '(empty)'}")
        if err:
            print(f"     Error:    {err}")

    print(f"\n{'=' * 60}")
    print("GAIA Benchmark Summary")
    print(f"{'=' * 60}")
    print(f"Total: {total}, Correct: {correct}, Accuracy: {accuracy:.3f}")
    print(f"Average runtime: {avg_runtime:.2f}s")
    if result_file:
        print(f"Results saved to: {result_file}")

    # Narrative note: this is the *intended* takeaway of running a general
    # benchmark against a domain-specialised agent.
    if accuracy < 0.2:
        print(f"\n{'-' * 60}")
        print("Why such low accuracy?")
        print(f"{'-' * 60}")
        print("The Financial Advisor agent is intentionally narrow-scope")
        print("(finance education only; no web search, no file analysis).")
        print("GAIA tests general-assistant capabilities, so off-domain")
        print("refusals are expected. This is a great example of using a")
        print("benchmark to *discover* scope mismatches: the integration")
        print("works, the agent just isn't built for these tasks.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run GAIA benchmark")
    parser.add_argument("--level", type=int, default=1, choices=[1, 2, 3])
    parser.add_argument("--max-n", type=int, default=3)
    parser.add_argument("--result-file", type=str, default=None)
    args = parser.parse_args()

    asyncio.run(main(level=args.level, max_n=args.max_n, result_file=args.result_file))
