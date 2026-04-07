# MAF Evaluations

Comprehensive evaluation suite built on **Microsoft Agent Framework (MAF) v1.0.0** for a **Financial Advisor** agent. Covers all MAF evaluation capabilities across 7 categories.

> **Tested and verified** on April 7, 2026 with `agent-framework==1.0.0`, `gpt-4.1`, and Azure AI Foundry.

---

## Prerequisites

- Python 3.10+
- Azure AI Foundry project with a deployed model (e.g. `gpt-4.1`)
- Azure CLI authenticated (`az login`)
- **Important**: the Storage Account linked to the Foundry project must have **public access enabled** (required for Foundry to write evaluation results)

### Optional prerequisites

- OpenAI API key (for TAU2 benchmark)
- Hugging Face token (for GAIA benchmark)

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Authenticate with Azure
az login

# 3. Configure environment variables
cp .env.example .env
# Edit .env with your values:
#   FOUNDRY_PROJECT_ENDPOINT=https://<your-project>.services.ai.azure.com/api/projects/<project-name>
#   FOUNDRY_MODEL=gpt-4.1
```

### Verify everything works

```bash
python -c "
import asyncio, sys; sys.path.insert(0, '.')
from src.utils import create_chat_client
from src.agents import create_financial_advisor
async def test():
    client = create_chat_client()
    agent = create_financial_advisor(client)
    r = await agent.run('What is compound interest? Be brief.')
    print(r.text[:200])
asyncio.run(test())
"
```

If you see a response about compound interest, you're all set.

---

## Usage guide by evaluation

### 01 — Local Eval (no evaluation API needed, fast, CI-friendly)

```bash
python evaluations/01_local_eval/run_local_eval.py
```

**What it does**: Evaluates the agent locally without cloud evaluation API calls. Only uses the model API to run the agent.

**Patterns demonstrated**:
- `keyword_check("C001")` — verifies the response contains expected keywords
- `tool_called_check("get_portfolio_summary")` — verifies the agent called the correct tool
- `@evaluator` — custom functions: `mentions_disclaimer`, `no_specific_stock_tips`, `response_length_ok`
- `ExpectedToolCall("get_risk_assessment", {"risk_level": "moderate"})` — verifies exact arguments
- `raise_for_status()` — raises an exception on failure (CI/CD integration)

**Runtime**: ~15-30 seconds
**Expected result**: All patterns pass

**Tip**: To reliably make the agent call a specific tool, be explicit in the query:
```python
# Unreliable: "What's a good strategy for moderate risk?"
# Reliable: "Use the get_risk_assessment tool for moderate risk level"
```

---

### 02a — Foundry: Agent Eval (cloud evaluation with Azure AI evaluators)

```bash
python evaluations/02_foundry_eval/run_agent_eval.py
```

**What it does**: Evaluates agent responses using Azure AI Foundry cloud evaluators (RELEVANCE, TOOL_CALL_ACCURACY, etc.).

**Patterns demonstrated**:
1. `evaluate_agent(responses=response)` — evaluate a response you already have
2. `evaluate_agent(queries=[...])` — run agent + evaluate in one call
3. `ConversationSplit.FULL` — evaluate full conversation trajectory vs last turn only

**Runtime**: ~60-90 seconds
**Expected result**: Links to Azure AI Foundry portal with detailed results

**Actual output**:
```
Pattern 1: Status: completed, Results: 1/1 passed
Pattern 2a: Status: completed, Results: 2/3 passed   <- real eval finding, 1 item may fail
Pattern 2b: Status: completed, Results: 1/1 passed
Portal: https://ai.azure.com/nextgen/r/.../build/evaluations/...
```

---

### 02b — Foundry: Tool Calls Eval

```bash
python evaluations/02_foundry_eval/run_tool_calls_eval.py
```

**What it does**: Evaluates tool usage accuracy using `AgentEvalConverter.to_eval_item()` for manual conversion.

**Runtime**: ~60 seconds
**Expected result**: 5/5 items with RELEVANCE and TOOL_CALL_ACCURACY scores (typically 5.0/5.0)

---

### 02c — Foundry: Multi-turn Eval

```bash
python evaluations/02_foundry_eval/run_multiturn_eval.py
```

**What it does**: Evaluates the same multi-turn conversation in 3 different ways:

| Strategy | What it evaluates |
|----------|------------------|
| `LAST_TURN` | Was the last response good given the context? |
| `FULL` | Did the whole conversation serve the original request? |
| `per_turn_items` | Was each individual response appropriate? |

**Runtime**: ~90 seconds
**Expected result**: All 3 strategies pass, with relevance scores 3-5 and coherence 3-4

---

### 02d — Foundry: Traces Eval (zero-code-change)

```bash
python evaluations/02_foundry_eval/run_traces_eval.py
```

**What it does**: Runs the agent with `store=True`, captures the `response_id` values, and then evaluates those stored responses without re-running the agent.

**Runtime**: ~90 seconds
**Expected result**: 2/2 passed with portal link

**Use case**: Evaluate agents in production without modifying agent code.

---

### 03 — Mixed Eval (local + cloud in a single call)

```bash
python evaluations/03_mixed_eval/run_mixed_eval.py
```

**What it does**: Combines `LocalEvaluator` (fast API-free checks) and `FoundryEvals` (deep cloud evaluation) in a single `evaluate_agent()` call.

**Patterns**:
1. Local only — instant, no API calls
2. Foundry only — deep cloud quality assessment
3. Mixed — `evaluators=[local, foundry]` returns one `EvalResults` per provider

**Runtime**: ~60 seconds
**Expected result**: Local and Foundry may give different results (that's the point!)

```
[PASS] Local: 1/1 passed            <- fast smoke checks
[PASS] Microsoft Foundry: 2/2       <- deep quality evaluation
```

---

### 04 — Red Teaming (adversarial safety testing)

```bash
python evaluations/04_red_teaming/run_red_team.py
```

**What it does**: Tests agent resilience against adversarial attacks using Azure AI RedTeam with pyrit.

**Attack strategies**: EASY, MODERATE, CharacterSpace, ROT13, Leetspeak, Base64+ROT13
**Risk categories**: Violence, HateUnfairness, Sexual, SelfHarm

**Runtime**: ~10-15 minutes (72+ attack attempts + scoring)

**Actual results obtained**:
```
Overall ASR: 3.33%            <- below the 5% production target
  Violence: 0%                <- no successful attacks
  Sexual: 0%                  <- no successful attacks
  Self-harm: 0%               <- no successful attacks
  Hate/unfairness: 13.33%     <- area for improvement
```

**Interpreting results**: ASR (Attack Success Rate) = percentage of attacks that bypassed the agent's defenses. Lower is better. Production target: < 5%.

**Extra requirement**: `pip install "azure-ai-evaluation[redteam]"` (already included in requirements.txt)

---

### 05 — Self-Reflection (iterative improvement with evaluation)

```bash
python evaluations/05_self_reflection/run_self_reflection.py
```

**What it does**: Implements the Reflexion pattern (NeurIPS 2023) — the agent generates a response, its groundedness is evaluated (1-5), and if not perfect, the agent is asked to improve iteratively.

**Flow**:
1. Generate response
2. Evaluate groundedness via `FoundryEvals` (score 1-5)
3. If score < 5 -> provide feedback to agent -> retry
4. Stop at perfect score or max iterations

**Runtime**: ~5 minutes (5 prompts x evaluations)

**Actual results obtained**:
```
5/5 prompts: Perfect score 5/5 on first try
Average best score: 5.00/5
```

---

### 06 — Workflow Eval (multi-agent workflow evaluation)

```bash
cd evaluations/06_workflow_eval && python run_workflow_eval.py
```

**What it does**: Creates a multi-agent workflow (fan-out/fan-in) and evaluates each agent individually:

```
request-handler -> +-> risk-assessment-agent    -+
                   +-> market-research-agent    -+-> financial-coordinator
                   +-> portfolio-analysis-agent -+
```

**Patterns**:
1. Post-hoc: `evaluate_workflow(workflow_result=result)` — evaluate an existing result
2. Run + evaluate: `evaluate_workflow(queries=[...])` — execute and evaluate

**Runtime**: ~3-5 minutes per pattern

**Actual result (Pattern 1)**:
```
Per-agent breakdown:
  request-handler: 0/1 passed         <- handler has little content of its own
  market-research-agent: 1/1 passed
  risk-assessment-agent: 1/1 passed
  portfolio-analysis-agent: 1/1 passed
```

---

### 07a — GAIA Benchmark (optional)

```bash
python evaluations/07_benchmarks/run_gaia.py --level 1 --max-n 3
```

**Requirements**: `HF_TOKEN` with access to the `gaia-benchmark/GAIA` dataset

---

### 07b — TAU2 Benchmark (optional)

```bash
python evaluations/07_benchmarks/run_tau2.py --assistant gpt-4o --max-steps 50
```

**Requirements**: `OPENAI_API_KEY`, tau2-bench data cloned locally

**Note**: The `agent-framework-lab[tau2]` module (v1.0.0b251024) has a compatibility issue with v1.0.0 of core. The script handles the error gracefully.

---

## Troubleshooting

### 401/403 error on Foundry evaluations

```
openai.AuthenticationError: ProjectMIUnauthorized
```

**Cause**: The Foundry project's Storage Account does not have public access enabled.
**Fix**: In Azure Portal -> Storage Account -> Networking -> enable public access.

### Agent doesn't call the expected tool

The model may decide to respond without using tools. For tests that require specific tool calls, include explicit instructions:
```python
queries=["Use the get_risk_assessment tool for moderate risk level"]
```

### ExperimentalWarning in console

```
ExperimentalWarning: [EVALS] ... is experimental
```

This is expected. The evaluation APIs in MAF v1.0.0 are marked as `@experimental`. They are functional and stable.

### Red teaming takes a long time

This is normal. Each run generates ~72 attack attempts (6 strategies x 4 categories x 3 objectives) + scoring. Expect 10-15 minutes.

### `evaluate_traces` fails with `missing model`

Requires the `model=` parameter explicitly:
```python
results = await evaluate_traces(
    response_ids=ids,
    evaluators=[FoundryEvals.RELEVANCE],
    client=client,
    model=client.model,  # <- required
)
```

---

## Project structure

```
MAFEvaluations/
+-- requirements.txt
+-- .env.example
+-- src/
|   +-- agents/
|   |   +-- tools.py                  # 5 mock financial tools (@tool decorated)
|   |   +-- financial_advisor.py      # Agent factory with safety instructions
|   +-- utils/
|       +-- common.py                 # Chat client creation (Foundry/OpenAI)
+-- evaluations/
    +-- 01_local_eval/                # LocalEvaluator, keyword_check, @evaluator
    +-- 02_foundry_eval/              # FoundryEvals, evaluate_agent, evaluate_traces
    +-- 03_mixed_eval/                # Local + Foundry combined
    +-- 04_red_teaming/               # RedTeam with AttackStrategy
    +-- 05_self_reflection/           # Reflexion pattern with groundedness
    +-- 06_workflow_eval/             # WorkflowBuilder + evaluate_workflow
    +-- 07_benchmarks/                # GAIA and TAU2
```

## MAF APIs used

| API | Package | Purpose |
|-----|---------|---------|
| `evaluate_agent()` | `agent_framework` | Run agent + evaluate in one call |
| `evaluate_workflow()` | `agent_framework` | Evaluate multi-agent workflows with per-agent breakdown |
| `LocalEvaluator` | `agent_framework` | Fast API-free checks, ideal for CI/CD |
| `@evaluator` | `agent_framework` | Decorator for custom evaluation functions |
| `keyword_check()`, `tool_called_check()` | `agent_framework` | Built-in check helpers |
| `ExpectedToolCall` | `agent_framework` | Verify expected tool calls with arguments |
| `FoundryEvals` | `agent_framework.foundry` | Azure AI Foundry cloud evaluators |
| `evaluate_traces()` | `agent_framework.foundry` | Evaluate past runs by response ID |
| `EvalItem`, `ConversationSplit` | `agent_framework` | Evaluation data types |
| `AgentEvalConverter` | `agent_framework` | Conversion to evaluation format |
| `WorkflowBuilder` | `agent_framework` | Multi-agent workflow construction |
| `RedTeam`, `AttackStrategy` | `azure.ai.evaluation` | Adversarial red teaming |
| `GAIA` | `agent_framework.lab.gaia` | GAIA benchmark |
| `TaskRunner` | `agent_framework.lab.tau2` | TAU2 benchmark |

## Available cloud evaluators (FoundryEvals)

| Category | Evaluators |
|----------|-----------|
| **Quality** | `RELEVANCE`, `GROUNDEDNESS`, `COHERENCE`, `FLUENCY`, `SIMILARITY`, `RESPONSE_COMPLETENESS` |
| **Tools** | `TOOL_CALL_ACCURACY`, `TOOL_SELECTION`, `TOOL_INPUT_ACCURACY`, `TOOL_OUTPUT_UTILIZATION`, `TOOL_CALL_SUCCESS` |
| **Agent behavior** | `INTENT_RESOLUTION`, `TASK_ADHERENCE`, `TASK_COMPLETION`, `TASK_NAVIGATION_EFFICIENCY` |
| **Safety** | `VIOLENCE`, `SEXUAL`, `SELF_HARM`, `HATE_UNFAIRNESS` |
