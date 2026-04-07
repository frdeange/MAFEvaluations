# MAF Evaluations

Suite de evaluaciones completa construida sobre **Microsoft Agent Framework (MAF) v1.0.0** para un agente **Financial Advisor**. Cubre todas las capacidades de evaluación del MAF en 7 categorías.

> **Probado y verificado** el 7 de abril de 2026 con `agent-framework==1.0.0`, `gpt-4.1` y Azure AI Foundry.

---

## Requisitos previos

- Python 3.10+
- Azure AI Foundry project con un modelo desplegado (ej: `gpt-4.1`)
- Azure CLI autenticado (`az login`)
- **Importante**: el Storage Account asociado al proyecto Foundry debe tener **acceso público habilitado** (necesario para que Foundry escriba resultados de evaluación)

### Requisitos opcionales

- OpenAI API key (para benchmark TAU2)
- Hugging Face token (para benchmark GAIA)

---

## Setup

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar credenciales Azure
az login

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus valores:
#   FOUNDRY_PROJECT_ENDPOINT=https://<tu-proyecto>.services.ai.azure.com/api/projects/<nombre-proyecto>
#   FOUNDRY_MODEL=gpt-4.1
```

### Verificar que funciona

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

Si ves una respuesta sobre interés compuesto, todo está listo.

---

## Guía de uso por evaluación

### 01 — Local Eval (sin API de evaluación, rápido, ideal para CI)

```bash
python evaluations/01_local_eval/run_local_eval.py
```

**Qué hace**: Evalúa al agente localmente sin llamadas API de evaluación. Solo usa la API del modelo para ejecutar el agente.

**Patrones demostrados**:
- `keyword_check("C001")` — verifica que la respuesta contiene keywords esperados
- `tool_called_check("get_portfolio_summary")` — verifica que el agente llamó al tool correcto
- `@evaluator` — funciones personalizadas: `mentions_disclaimer`, `no_specific_stock_tips`, `response_length_ok`
- `ExpectedToolCall("get_risk_assessment", {"risk_level": "moderate"})` — verifica argumentos exactos
- `raise_for_status()` — lanza excepción si falla (integración CI/CD)

**Tiempo**: ~15-30 segundos  
**Resultado esperado**: Todos los patrones pasan ✅

**Consejo**: Para que el agente llame a un tool específico de forma fiable, sé explícito en la query:
```python
# ❌ Poco fiable: "What's a good strategy for moderate risk?"
# ✅ Fiable: "Use the get_risk_assessment tool for moderate risk level"
```

---

### 02a — Foundry: Agent Eval (evaluación cloud con evaluadores de Azure AI)

```bash
python evaluations/02_foundry_eval/run_agent_eval.py
```

**Qué hace**: Evalúa respuestas del agente usando evaluadores cloud de Azure AI Foundry (RELEVANCE, TOOL_CALL_ACCURACY, etc.).

**Patrones demostrados**:
1. `evaluate_agent(responses=response)` — evalúa una respuesta que ya tienes
2. `evaluate_agent(queries=[...])` — ejecuta el agente + evalúa en una sola llamada
3. `ConversationSplit.FULL` — evalúa toda la trayectoria de conversación vs solo el último turno

**Tiempo**: ~60-90 segundos  
**Resultado esperado**: Links al portal de Azure AI Foundry con resultados detallados

**Salida real**:
```
Pattern 1: Status: completed, Results: 1/1 passed
Pattern 2a: Status: completed, Results: 2/3 passed   ← eval real, 1 item puede fallar
Pattern 2b: Status: completed, Results: 1/1 passed
Portal: https://ai.azure.com/nextgen/r/.../build/evaluations/...
```

---

### 02b — Foundry: Tool Calls Eval

```bash
python evaluations/02_foundry_eval/run_tool_calls_eval.py
```

**Qué hace**: Evalúa la precisión del uso de herramientas usando `AgentEvalConverter.to_eval_item()` para conversión manual.

**Tiempo**: ~60 segundos  
**Resultado esperado**: 5/5 items con RELEVANCE y TOOL_CALL_ACCURACY scores (típicamente 5.0/5.0)

---

### 02c — Foundry: Multi-turn Eval

```bash
python evaluations/02_foundry_eval/run_multiturn_eval.py
```

**Qué hace**: Evalúa la misma conversación multi-turno de 3 formas distintas:

| Estrategia | Qué evalúa |
|------------|-----------|
| `LAST_TURN` | ¿Fue buena la última respuesta dado el contexto? |
| `FULL` | ¿Toda la conversación sirvió a la petición original? |
| `per_turn_items` | ¿Fue apropiada cada respuesta individual? |

**Tiempo**: ~90 segundos  
**Resultado esperado**: Las 3 estrategias pasan, con scores de relevance 3-5 y coherence 3-4

---

### 02d — Foundry: Traces Eval (zero-code-change)

```bash
python evaluations/02_foundry_eval/run_traces_eval.py
```

**Qué hace**: Ejecuta el agente con `store=True`, captura los `response_id`, y después evalúa esas respuestas almacenadas sin volver a ejecutar el agente.

**Tiempo**: ~90 segundos  
**Resultado esperado**: 2/2 passed con link al portal

**Caso de uso**: Evaluar agentes en producción sin modificar el código del agente.

---

### 03 — Mixed Eval (local + cloud en una sola llamada)

```bash
python evaluations/03_mixed_eval/run_mixed_eval.py
```

**Qué hace**: Combina `LocalEvaluator` (checks rápidos sin API) y `FoundryEvals` (evaluación cloud) en una sola llamada a `evaluate_agent()`.

**Patrones**:
1. Solo local — instantáneo, sin API
2. Solo Foundry — evaluación cloud profunda
3. Mixto — `evaluators=[local, foundry]` → devuelve un `EvalResults` por proveedor

**Tiempo**: ~60 segundos  
**Resultado esperado**: Local y Foundry pueden dar resultados diferentes (¡ese es el punto!)

```
[PASS] Local: 1/1 passed          ← checks rápidos
[PASS] Microsoft Foundry: 2/2     ← evaluación de calidad profunda
```

---

### 04 — Red Teaming (test adversarial de seguridad)

```bash
python evaluations/04_red_teaming/run_red_team.py
```

**Qué hace**: Prueba la resiliencia del agente contra ataques adversariales usando Azure AI RedTeam con pyrit.

**Estrategias de ataque**: EASY, MODERATE, CharacterSpace, ROT13, Leetspeak, Base64+ROT13  
**Categorías de riesgo**: Violence, HateUnfairness, Sexual, SelfHarm

**⚠️ Tiempo**: ~10-15 minutos (72+ intentos de ataque + scoring)

**Resultado real obtenido**:
```
Overall ASR: 3.33%          ← por debajo del 5% target ✅
  Violence: 0%              ← ningún ataque exitoso
  Sexual: 0%                ← ningún ataque exitoso  
  Self-harm: 0%             ← ningún ataque exitoso
  Hate/unfairness: 13.33%   ← área de mejora ⚠️
```

**Interpretar resultados**: ASR (Attack Success Rate) = porcentaje de ataques que lograron evadir las defensas del agente. Menor es mejor. Target para producción: < 5%.

**Requisito extra**: `pip install "azure-ai-evaluation[redteam]"` (ya incluido en requirements.txt)

---

### 05 — Self-Reflection (mejora iterativa con evaluación)

```bash
python evaluations/05_self_reflection/run_self_reflection.py
```

**Qué hace**: Implementa el patrón Reflexion (NeurIPS 2023) — el agente genera una respuesta, se evalúa su groundedness (1-5), y si no es perfecta, se le pide que mejore iterativamente.

**Flujo**:
1. Generar respuesta
2. Evaluar groundedness con `FoundryEvals` (score 1-5)
3. Si score < 5 → feedback al agente → reintentar
4. Parar en score perfecto o máx iteraciones

**Tiempo**: ~5 minutos (5 prompts × evaluaciones)

**Resultado real obtenido**:
```
5/5 prompts: Perfect score 5/5 on first try ✅
Average best score: 5.00/5
```

---

### 06 — Workflow Eval (evaluación de workflows multi-agente)

```bash
cd evaluations/06_workflow_eval && python run_workflow_eval.py
```

**Qué hace**: Crea un workflow multi-agente (fan-out/fan-in) y evalúa cada agente individualmente:

```
request-handler → ┬→ risk-assessment-agent    ─┐
                   ├→ market-research-agent    ─┼→ financial-coordinator
                   └→ portfolio-analysis-agent ─┘
```

**Patrones**:
1. Post-hoc: `evaluate_workflow(workflow_result=result)` — evalúa un resultado ya existente
2. Run + evaluate: `evaluate_workflow(queries=[...])` — ejecuta y evalúa

**Tiempo**: ~3-5 minutos por patrón

**Resultado real (Pattern 1)**:
```
Per-agent breakdown:
  request-handler: 0/1 passed       ← el handler tiene poco contenido propio
  market-research-agent: 1/1 passed  ✅
  risk-assessment-agent: 1/1 passed  ✅
  portfolio-analysis-agent: 1/1 passed ✅
```

---

### 07a — GAIA Benchmark (opcional)

```bash
python evaluations/07_benchmarks/run_gaia.py --level 1 --max-n 3
```

**Requisitos**: `HF_TOKEN` con acceso al dataset `gaia-benchmark/GAIA`

---

### 07b — TAU2 Benchmark (opcional)

```bash
python evaluations/07_benchmarks/run_tau2.py --assistant gpt-4o --max-steps 50
```

**Requisitos**: `OPENAI_API_KEY`, datos de tau2-bench clonados

**Nota**: El módulo `agent-framework-lab[tau2]` (v1.0.0b251024) tiene un problema de compatibilidad con la v1.0.0 del core. El script maneja el error graciosamente.

---

## Troubleshooting

### Error 401/403 en evaluaciones Foundry

```
openai.AuthenticationError: ProjectMIUnauthorized
```

**Causa**: El Storage Account del proyecto Foundry no tiene acceso público habilitado.  
**Solución**: En Azure Portal → Storage Account → Networking → habilitar acceso público.

### El agente no llama al tool esperado

El modelo puede decidir responder sin usar tools. Para tests que requieren tool calls específicos, incluye instrucciones explícitas:
```python
queries=["Use the get_risk_assessment tool for moderate risk level"]
```

### ExperimentalWarning en consola

```
ExperimentalWarning: [EVALS] ... is experimental
```

Esto es esperado. Las APIs de evaluación en MAF v1.0.0 están marcadas como `@experimental`. Son funcionales y estables.

### Red teaming tarda mucho

Es normal. Cada ejecución genera ~72 intentos de ataque (6 estrategias × 4 categorías × 3 objetivos) + scoring. Espera 10-15 minutos.

### `evaluate_traces` falla con `missing model`

Requiere el parámetro `model=` explícito:
```python
results = await evaluate_traces(
    response_ids=ids,
    evaluators=[FoundryEvals.RELEVANCE],
    client=client,
    model=client.model,  # ← obligatorio
)
```

---

## Estructura del proyecto

```
MAFEvaluations/
├── requirements.txt
├── .env.example
├── src/
│   ├── agents/
│   │   ├── tools.py                  # 5 herramientas mock (@tool)
│   │   └── financial_advisor.py      # Factory del agente con instrucciones de seguridad
│   └── utils/
│       └── common.py                 # Creación de chat client (Foundry/OpenAI)
└── evaluations/
    ├── 01_local_eval/                # LocalEvaluator, keyword_check, @evaluator
    ├── 02_foundry_eval/              # FoundryEvals, evaluate_agent, evaluate_traces
    ├── 03_mixed_eval/                # Local + Foundry combinados
    ├── 04_red_teaming/               # RedTeam con AttackStrategy
    ├── 05_self_reflection/           # Patrón Reflexion con groundedness
    ├── 06_workflow_eval/             # WorkflowBuilder + evaluate_workflow
    └── 07_benchmarks/                # GAIA y TAU2
```

## APIs del MAF utilizadas

| API | Paquete | Propósito |
|-----|---------|-----------|
| `evaluate_agent()` | `agent_framework` | Ejecutar agente + evaluar en una llamada |
| `evaluate_workflow()` | `agent_framework` | Evaluar workflows multi-agente con breakdown por agente |
| `LocalEvaluator` | `agent_framework` | Checks rápidos sin API, ideal para CI/CD |
| `@evaluator` | `agent_framework` | Decorador para funciones de evaluación custom |
| `keyword_check()`, `tool_called_check()` | `agent_framework` | Helpers de checks built-in |
| `ExpectedToolCall` | `agent_framework` | Verificar tool calls esperados con argumentos |
| `FoundryEvals` | `agent_framework.foundry` | Evaluadores cloud de Azure AI Foundry |
| `evaluate_traces()` | `agent_framework.foundry` | Evaluar ejecuciones pasadas por response ID |
| `EvalItem`, `ConversationSplit` | `agent_framework` | Tipos de datos de evaluación |
| `AgentEvalConverter` | `agent_framework` | Conversión a formato de evaluación |
| `WorkflowBuilder` | `agent_framework` | Construcción de workflows multi-agente |
| `RedTeam`, `AttackStrategy` | `azure.ai.evaluation` | Red teaming adversarial |
| `GAIA` | `agent_framework.lab.gaia` | Benchmark GAIA |
| `TaskRunner` | `agent_framework.lab.tau2` | Benchmark TAU2 |

## Evaluadores cloud disponibles (FoundryEvals)

| Categoría | Evaluadores |
|-----------|-------------|
| **Calidad** | `RELEVANCE`, `GROUNDEDNESS`, `COHERENCE`, `FLUENCY`, `SIMILARITY`, `RESPONSE_COMPLETENESS` |
| **Herramientas** | `TOOL_CALL_ACCURACY`, `TOOL_SELECTION`, `TOOL_INPUT_ACCURACY`, `TOOL_OUTPUT_UTILIZATION`, `TOOL_CALL_SUCCESS` |
| **Comportamiento** | `INTENT_RESOLUTION`, `TASK_ADHERENCE`, `TASK_COMPLETION`, `TASK_NAVIGATION_EFFICIENCY` |
| **Seguridad** | `VIOLENCE`, `SEXUAL`, `SELF_HARM`, `HATE_UNFAIRNESS` |
