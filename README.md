# MAF Evaluations

Comprehensive evaluation suite built on **Microsoft Agent Framework (MAF) v1.0.0** for a **Financial Advisor** agent. Covers all MAF evaluation capabilities across 7 categories.

## Prerequisites

- Python 3.10+
- Azure AI Foundry project (for cloud evaluations, red teaming, self-reflection)
- Azure CLI authenticated (`az login`)
- OpenAI API key (for TAU2 benchmark)
- Hugging Face token (for GAIA benchmark)

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

## Evaluations

| # | Category | Script | API Needed | Description |
|---|----------|--------|------------|-------------|
| 01 | **Local Eval** | `evaluations/01_local_eval/run_local_eval.py` | Any provider | Built-in checks, custom `@evaluator` functions, expected tool calls. No cloud API for eval logic. |
| 02a | **Foundry: Agent** | `evaluations/02_foundry_eval/run_agent_eval.py` | Foundry | `evaluate_agent()` with RELEVANCE, GROUNDEDNESS, TOOL_CALL_ACCURACY |
| 02b | **Foundry: Tool Calls** | `evaluations/02_foundry_eval/run_tool_calls_eval.py` | Foundry | Manual `AgentEvalConverter` + TOOL_CALL_ACCURACY |
| 02c | **Foundry: Multi-turn** | `evaluations/02_foundry_eval/run_multiturn_eval.py` | Foundry | LAST_TURN, FULL, and per_turn_items split strategies |
| 02d | **Foundry: Traces** | `evaluations/02_foundry_eval/run_traces_eval.py` | Foundry | `evaluate_traces()` — zero-code-change past run eval |
| 03 | **Mixed Eval** | `evaluations/03_mixed_eval/run_mixed_eval.py` | Foundry | `LocalEvaluator` + `FoundryEvals` in single call |
| 04 | **Red Teaming** | `evaluations/04_red_teaming/run_red_team.py` | Foundry | Adversarial attack scan with 6 strategies, ASR scorecard |
| 05 | **Self-Reflection** | `evaluations/05_self_reflection/run_self_reflection.py` | Foundry | Iterative groundedness improvement (Reflexion pattern) |
| 06 | **Workflow Eval** | `evaluations/06_workflow_eval/run_workflow_eval.py` | Foundry | Multi-agent workflow with per-agent breakdown |
| 07a | **GAIA Benchmark** | `evaluations/07_benchmarks/run_gaia.py` | Any + HF_TOKEN | General AI Assistant benchmark (levels 1-3) |
| 07b | **TAU2 Benchmark** | `evaluations/07_benchmarks/run_tau2.py` | OpenAI | Customer service benchmark (airline domain) |

## Quick Start

```bash
# 1. Local evaluation (works with any provider, no cloud eval API needed)
python evaluations/01_local_eval/run_local_eval.py

# 2. Foundry cloud evaluation
python evaluations/02_foundry_eval/run_agent_eval.py

# 3. Mixed local + cloud
python evaluations/03_mixed_eval/run_mixed_eval.py

# 4. Red teaming (requires azure-ai-evaluation + pyrit)
python evaluations/04_red_teaming/run_red_team.py

# 5. Self-reflection loop
python evaluations/05_self_reflection/run_self_reflection.py

# 6. Multi-agent workflow evaluation
cd evaluations/06_workflow_eval && python run_workflow_eval.py

# 7. Benchmarks
python evaluations/07_benchmarks/run_gaia.py --level 1 --max-n 5
python evaluations/07_benchmarks/run_tau2.py --assistant gpt-4o --max-steps 50
```

## Project Structure

```
MAFEvaluations/
├── requirements.txt
├── .env.example
├── src/
│   ├── agents/
│   │   ├── tools.py                  # Mock financial tools (@tool decorated)
│   │   └── financial_advisor.py      # Agent factory with safety instructions
│   └── utils/
│       └── common.py                 # Chat client creation (Foundry/OpenAI)
└── evaluations/
    ├── 01_local_eval/                # LocalEvaluator, keyword_check, @evaluator
    ├── 02_foundry_eval/              # FoundryEvals, evaluate_agent, evaluate_traces
    ├── 03_mixed_eval/                # Local + Foundry combined
    ├── 04_red_teaming/               # RedTeam with AttackStrategy
    ├── 05_self_reflection/           # Reflexion pattern with groundedness
    ├── 06_workflow_eval/             # WorkflowBuilder + evaluate_workflow
    └── 07_benchmarks/                # GAIA and TAU2
```

## Key MAF APIs Used

| API | Package | Purpose |
|-----|---------|---------|
| `evaluate_agent()` | `agent_framework` | Run agent + evaluate in one call |
| `evaluate_workflow()` | `agent_framework` | Evaluate multi-agent workflows |
| `LocalEvaluator` | `agent_framework` | Fast, API-free local checks |
| `@evaluator` | `agent_framework` | Custom check functions |
| `keyword_check()`, `tool_called_check()` | `agent_framework` | Built-in check helpers |
| `FoundryEvals` | `agent_framework.foundry` | Azure AI Foundry cloud evaluators |
| `evaluate_traces()` | `agent_framework.foundry` | Evaluate past runs by response ID |
| `EvalItem`, `ConversationSplit` | `agent_framework` | Evaluation data types |
| `WorkflowBuilder` | `agent_framework` | Multi-agent workflow construction |
| `GAIA` | `agent_framework.lab.gaia` | GAIA benchmark runner |
| `TaskRunner` | `agent_framework.lab.tau2` | TAU2 benchmark runner |
