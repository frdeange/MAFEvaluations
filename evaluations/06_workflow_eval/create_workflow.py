# Copyright (c) MAFEvaluations project. All rights reserved.

"""Multi-agent financial advisory workflow for evaluation.

Workflow structure (fan-out / fan-in):
  start → request_handler → [risk_agent, market_agent, portfolio_agent] → coordinator

Agents:
1. Request Handler — Parses user query and relays to specialists
2. Risk Assessment Agent — Uses get_risk_assessment tool
3. Market Research Agent — Uses get_market_data, search_investment_options tools
4. Portfolio Analysis Agent — Uses get_portfolio_summary, calculate_returns tools
5. Financial Coordinator — Aggregates findings into a comprehensive recommendation
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agent_framework import (
    Agent,
    AgentExecutorResponse,
    Executor,
    Message,
    WorkflowBuilder,
    WorkflowContext,
    executor,
    handler,
)

from src.agents.tools import (
    calculate_returns,
    get_market_data,
    get_portfolio_summary,
    get_risk_assessment,
    search_investment_options,
)


@executor(id="start_executor")
async def start_executor(input: str, ctx: WorkflowContext[list[Message]]) -> None:
    """Initiates the workflow by sending the user query to all agents."""
    await ctx.send_message([Message("user", [input])])


class FinancialCoordinator(Executor):
    """Aggregates findings from all specialist agents into a recommendation."""

    def __init__(self, client, id: str = "financial-coordinator"):
        self.agent = Agent(
            client=client,
            id="financial-coordinator",
            instructions=(
                "You are the final financial coordinator. You receive responses from: "
                "risk-assessment-agent, market-research-agent, and portfolio-analysis-agent. "
                "Synthesize their findings into a clear, comprehensive financial recommendation. "
                "Structure your response as: "
                "1. Risk Profile Summary  2. Market Overview  3. Portfolio Analysis  "
                "4. Recommended Actions. "
                "Include a disclaimer that this is general information. Do not use tools."
            ),
            name="financial-coordinator",
            default_options={"store": False},
        )
        super().__init__(id=id)

    @handler
    async def fan_in_handle(self, responses: list[AgentExecutorResponse], ctx: WorkflowContext) -> None:
        user_query = responses[0].full_conversation[0].text if responses[0].full_conversation else "financial advice"

        findings = []
        for resp in responses:
            if resp.agent_response and resp.agent_response.messages:
                texts = [m.text for m in resp.agent_response.messages if m.role == "assistant" and m.text]
                if texts:
                    findings.append(f"[{resp.executor_id}]: {' '.join(texts)}")

        summary = "\n".join(findings) if findings else "No findings provided."

        messages = [
            Message("system", [
                "Synthesize the specialist agent findings into a comprehensive financial recommendation."
            ]),
            Message("user", [
                f"Original query: {user_query}\n\nSpecialist findings:\n{summary}\n\n"
                "Provide a comprehensive financial recommendation based on these findings."
            ]),
        ]

        try:
            final_response = await self.agent.run(messages)
            output = final_response.messages[-1].text if final_response.messages else summary
        except Exception:
            output = f"Based on the specialist findings: {summary}"

        await ctx.yield_output(output)


def create_financial_workflow(client):
    """Create the multi-agent financial advisory workflow.

    Args:
        client: Chat client instance.

    Returns:
        Tuple of (workflow, agent_map).
    """
    coordinator = FinancialCoordinator(client=client, id="financial-coordinator")

    request_handler = Agent(
        client=client,
        id="request-handler",
        instructions=(
            "You receive financial queries and relay them to specialist agents. "
            "Extract key details: risk tolerance, investment goals, time horizon, budget. "
            "Pass this information forward clearly."
        ),
        name="request-handler",
        default_options={"store": False},
    )

    risk_agent = Agent(
        client=client,
        id="risk-assessment-agent",
        instructions=(
            "You are a risk assessment specialist. Use get_risk_assessment to evaluate "
            "the user's risk tolerance and provide allocation recommendations. "
            "Output ONLY risk assessment information."
        ),
        name="risk-assessment-agent",
        tools=[get_risk_assessment],
        default_options={"store": False},
    )

    market_agent = Agent(
        client=client,
        id="market-research-agent",
        instructions=(
            "You are a market research specialist. Use get_market_data and "
            "search_investment_options to find relevant market data and investment options. "
            "Output ONLY market data and available options."
        ),
        name="market-research-agent",
        tools=[get_market_data, search_investment_options],
        default_options={"store": False},
    )

    portfolio_agent = Agent(
        client=client,
        id="portfolio-analysis-agent",
        instructions=(
            "You are a portfolio analysis specialist. Use get_portfolio_summary and "
            "calculate_returns to analyze portfolios and project returns. "
            "Output ONLY portfolio analysis information."
        ),
        name="portfolio-analysis-agent",
        tools=[get_portfolio_summary, calculate_returns],
        default_options={"store": False},
    )

    workflow = (
        WorkflowBuilder(name="Financial Advisory Workflow", start_executor=start_executor)
        .add_edge(start_executor, request_handler)
        .add_fan_out_edges(request_handler, [risk_agent, market_agent, portfolio_agent])
        .add_fan_in_edges([risk_agent, market_agent, portfolio_agent], coordinator)
        .build()
    )

    agent_map = {
        "request-handler": request_handler,
        "risk-assessment-agent": risk_agent,
        "market-research-agent": market_agent,
        "portfolio-analysis-agent": portfolio_agent,
        "financial-coordinator": coordinator.agent,
    }

    return workflow, agent_map


async def demo():
    """Quick demo of the workflow."""
    from src.utils import create_chat_client

    client = create_chat_client()
    workflow, _ = create_financial_workflow(client)

    query = "I'm 35, have $100,000 to invest with moderate risk tolerance. What do you recommend?"
    print(f"Query: {query}\n")

    result = await workflow.run(query)
    outputs = result.get_outputs()
    if outputs:
        print(f"Recommendation:\n{outputs[-1]}")


if __name__ == "__main__":
    asyncio.run(demo())
