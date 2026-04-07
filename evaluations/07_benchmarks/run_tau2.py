# Copyright (c) MAFEvaluations project. All rights reserved.

"""Run the TAU2 benchmark for customer service agent evaluation.

TAU2 (τ²-bench) evaluates agents on multi-turn customer service tasks
with tool use, policy adherence, and realistic user simulation.

Prerequisites:
- pip install "agent-framework-lab[tau2]"
- pip install "tau2 @ git+https://github.com/sierra-research/tau2-bench@5ba9e3e56db57c5e4114bf7f901291f09b2c5619"
- Clone and extract tau2-bench data (see README)
- Set OPENAI_API_KEY and OPENAI_BASE_URL in .env
- Set TAU2_DATA_DIR=data

Run:
    python evaluations/07_benchmarks/run_tau2.py
    python evaluations/07_benchmarks/run_tau2.py --assistant gpt-4o --user gpt-4o-mini --max-steps 50
"""

import argparse
import asyncio
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv

load_dotenv()


async def main(assistant_model: str, user_model: str, max_steps: int, debug_task_id: str | None) -> None:
    print("=" * 60)
    print("  TAU2 Benchmark — Customer Service Agent")
    print("=" * 60)

    # Check prerequisites
    try:
        from agent_framework.lab.tau2 import TaskRunner, patch_env_set_state
        from agent_framework.openai import OpenAIChatClient
        from tau2.domains.airline.environment import get_tasks
    except ImportError as e:
        print(f"\nMissing dependency: {e}")
        print("Install with:")
        print('  pip install "agent-framework-lab[tau2]"')
        print('  pip install "tau2 @ git+https://github.com/sierra-research/tau2-bench@5ba9e3e56db57c5e4114bf7f901291f09b2c5619"')
        return

    base_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\nError: OPENAI_API_KEY not set. TAU2 requires OpenAI API access.")
        return

    # Apply environment patch for tau2-bench compatibility
    patch_env_set_state()

    tasks = get_tasks()
    print(f"\nLoaded {len(tasks)} tasks")
    print(f"Assistant model: {assistant_model}")
    print(f"User model: {user_model}")
    print(f"Max steps: {max_steps}")

    if debug_task_id:
        tasks = [t for t in tasks if t.id == debug_task_id]
        if not tasks:
            print(f"Task {debug_task_id} not found.")
            return
        print(f"Debug mode: running task {debug_task_id}")

    client_kwargs = {"api_key": api_key, "model": assistant_model}
    if base_url:
        client_kwargs["base_url"] = base_url

    assistant_client = OpenAIChatClient(**client_kwargs)

    user_kwargs = {"api_key": api_key, "model": user_model}
    if base_url:
        user_kwargs["base_url"] = base_url

    user_client = OpenAIChatClient(**user_kwargs)

    task_runner = TaskRunner(max_steps=max_steps)
    all_rewards: list[float] = []

    # Output file
    result_filename = None
    if not debug_task_id:
        os.makedirs("evaluations/07_benchmarks/results", exist_ok=True)
        timestamp = datetime.now().strftime("%m%d%H%M")
        result_filename = f"evaluations/07_benchmarks/results/tau2_{assistant_model}_{timestamp}.jsonl"
        print(f"Results: {result_filename}\n")

    for task in tasks:
        print(f"Task #{task.id}: {task.description.purpose if task.description else 'N/A'}")

        reward_value = 0.0
        try:
            conversation = await task_runner.run(task, assistant_client, user_client)
            reward_value = task_runner.evaluate(task, conversation, task_runner.termination_reason)
            print(f"  Reward: {reward_value}")
        except Exception as e:
            print(f"  Error: {e}")
            traceback.print_exc()

        all_rewards.append(reward_value)

        if result_filename:
            result_data: dict[str, Any] = {
                "id": task.id,
                "reward": reward_value,
                "config": {"assistant": assistant_model, "user": user_model},
            }
            with open(result_filename, "a") as f:
                f.write(json.dumps(result_data, default=str) + "\n")

        task_runner.reinit()

    # Summary
    accuracy = sum(all_rewards) / len(all_rewards) if all_rewards else 0.0
    print(f"\n{'=' * 60}")
    print("TAU2 Benchmark Summary")
    print(f"{'=' * 60}")
    print(f"Tasks: {len(all_rewards)}")
    print(f"Accuracy: {accuracy:.2f} ({int(sum(all_rewards))}/{len(all_rewards)})")
    if result_filename:
        print(f"Results saved to: {result_filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run TAU2 benchmark")
    parser.add_argument("--assistant", type=str, default="gpt-4o")
    parser.add_argument("--user", type=str, default="gpt-4o-mini")
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--debug-task-id", type=str, default=None)
    args = parser.parse_args()

    asyncio.run(main(
        assistant_model=args.assistant,
        user_model=args.user,
        max_steps=args.max_steps,
        debug_task_id=args.debug_task_id,
    ))
