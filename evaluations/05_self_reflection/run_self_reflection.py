# Copyright (c) MAFEvaluations project. All rights reserved.

"""Self-reflection evaluation using groundedness scoring.

Implements the Reflexion pattern (NeurIPS 2023): iteratively improve agent
responses based on groundedness evaluation from FoundryEvals.

Each prompt is processed through a loop:
  1. Generate response
  2. Evaluate groundedness via FoundryEvals (1-5 scale)
  3. If score < 5, provide feedback and retry
  4. Stop at perfect score or max iterations

Prerequisites:
- Azure AI Foundry project
- Set FOUNDRY_PROJECT_ENDPOINT in .env

Run:
    python evaluations/05_self_reflection/run_self_reflection.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import Agent, EvalItem, Message
from agent_framework.foundry import FoundryChatClient, FoundryEvals
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()


async def evaluate_groundedness(
    evals: FoundryEvals,
    query: str,
    response: str,
    context: str,
) -> float | None:
    """Run a single groundedness evaluation and return the score."""
    item = EvalItem(
        conversation=[
            Message("user", [query]),
            Message("assistant", [response]),
        ],
        context=context,
    )
    results = await evals.evaluate([item], eval_name="Self-Reflection Groundedness")
    if results.status != "completed" or not results.items:
        return None
    for score in results.items[0].scores:
        if score.score is not None:
            return float(score.score)
    return None


async def execute_with_self_reflection(
    *,
    evals: FoundryEvals,
    agent: Agent,
    full_user_query: str,
    context: str,
    max_reflections: int = 3,
) -> dict[str, Any]:
    """Execute a query with iterative self-reflection based on groundedness."""
    messages = [Message("user", [full_user_query])]

    best_score = 0.0
    max_score = 5
    best_response = None
    best_iteration = 0
    raw_response = None
    total_eval_time = 0.0
    start_time = time.time()
    iteration_scores: list[float] = []

    for i in range(max_reflections):
        print(f"  Self-reflection iteration {i + 1}/{max_reflections}...")

        raw_response = await agent.run(messages=messages)
        agent_response = raw_response.text

        t0 = time.time()
        score = await evaluate_groundedness(evals, full_user_query, agent_response, context)
        total_eval_time += time.time() - t0

        if score is None:
            print(f"  Warning: Groundedness evaluation failed for iteration {i + 1}.")
            continue

        iteration_scores.append(score)
        print(f"  Groundedness score: {score}/{max_score}")

        if score > best_score:
            if best_score > 0:
                print(f"  [IMPROVED] Score improved from {best_score} to {score}/{max_score}")
            best_score = score
            best_response = agent_response
            best_iteration = i + 1
            if score == max_score:
                print("  [PASS] Perfect groundedness score achieved!")
                break
        else:
            print(f"  -> No improvement (score: {score}/{max_score}). Trying again...")

        messages.append(Message("assistant", [agent_response]))
        messages.append(Message("user", [
            f"The groundedness score of your response is {score}/{max_score}. "
            f"Reflect on your answer and improve it to get the maximum score of {max_score}. "
            "Ensure your response is fully grounded in the provided context."
        ]))

    end_time = time.time()

    if best_response is None and raw_response is not None and raw_response.messages:
        best_response = raw_response.messages[0].text
        best_iteration = i + 1

    return {
        "best_response": best_response,
        "best_response_score": best_score,
        "best_iteration": best_iteration,
        "iteration_scores": iteration_scores,
        "num_retries": i + 1,
        "total_eval_time": total_eval_time,
        "total_time": end_time - start_time,
    }


async def main() -> None:
    print("=" * 60)
    print("  Self-Reflection Evaluation — Financial Advisor")
    print("=" * 60)

    credential = AzureCliCredential()
    client = FoundryChatClient(credential=credential)

    evals = FoundryEvals(
        client=client,
        evaluators=[FoundryEvals.GROUNDEDNESS],
    )

    # Load prompts
    prompts_file = Path(__file__).parent / "prompts.jsonl"
    with open(prompts_file) as f:
        prompts = json.load(f)

    print(f"Loaded {len(prompts)} prompts")
    print(f"Max self-reflections: 3\n")

    results = []
    successful = 0
    failed = 0

    for counter, prompt in enumerate(prompts, start=1):
        print(f"[{counter}/{len(prompts)}] Processing: {prompt['user_request'][:60]}...")

        try:
            agent = Agent(client=client, instructions=prompt["system_instruction"])

            result = await execute_with_self_reflection(
                evals=evals,
                agent=agent,
                full_user_query=prompt["full_prompt"],
                context=prompt["context_document"],
                max_reflections=3,
            )

            results.append(result)
            successful += 1
            print(
                f"  [PASS] Completed with score: {result['best_response_score']}/5 "
                f"(best at iteration {result['best_iteration']}/{result['num_retries']}, "
                f"time: {result['total_time']:.1f}s)\n"
            )
        except Exception as e:
            results.append({"error": str(e)})
            failed += 1
            print(f"  [FAIL] Error: {e}\n")

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total prompts: {len(prompts)}")
    print(f"  [PASS] Successful: {successful}")
    print(f"  [FAIL] Failed: {failed}")

    valid_results = [r for r in results if "best_response_score" in r]
    if valid_results:
        scores = [r["best_response_score"] for r in valid_results]
        avg_score = sum(scores) / len(scores)
        perfect = sum(1 for s in scores if s == 5)
        print(f"\nGroundedness Scores:")
        print(f"  Average best score: {avg_score:.2f}/5")
        print(f"  Perfect scores (5/5): {perfect}/{len(scores)} ({100 * perfect / len(scores):.1f}%)")

        iterations = [r["iteration_scores"] for r in valid_results if r["iteration_scores"]]
        if iterations:
            first_scores = [s[0] for s in iterations]
            last_scores = [s[-1] for s in iterations]
            avg_first = sum(first_scores) / len(first_scores)
            avg_last = sum(last_scores) / len(last_scores)
            print(f"\nImprovement Analysis:")
            print(f"  Average first score: {avg_first:.2f}/5")
            print(f"  Average final score: {avg_last:.2f}/5")
            print(f"  Average improvement: +{avg_last - avg_first:.2f}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
