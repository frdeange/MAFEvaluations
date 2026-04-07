# Copyright (c) MAFEvaluations project. All rights reserved.

import json
from typing import Annotated

from agent_framework import tool
from pydantic import Field


@tool(name="get_portfolio_summary", description="Get a summary of the client's investment portfolio.")
def get_portfolio_summary(
    client_id: Annotated[str, Field(description="The unique client identifier.")],
) -> str:
    """Get a summary of the client's investment portfolio including holdings and allocation."""
    portfolios = {
        "C001": {
            "client_id": "C001",
            "name": "Jane Smith",
            "total_value": "$245,000",
            "holdings": [
                {"asset": "S&P 500 ETF (VOO)", "allocation": "40%", "value": "$98,000", "return_ytd": "+12.3%"},
                {"asset": "Bond Fund (BND)", "allocation": "25%", "value": "$61,250", "return_ytd": "+3.1%"},
                {"asset": "International ETF (VXUS)", "allocation": "20%", "value": "$49,000", "return_ytd": "+8.7%"},
                {"asset": "Cash/Money Market", "allocation": "15%", "value": "$36,750", "return_ytd": "+4.5%"},
            ],
            "risk_profile": "Moderate",
            "last_rebalanced": "2025-11-15",
        },
        "C002": {
            "client_id": "C002",
            "name": "John Doe",
            "total_value": "$520,000",
            "holdings": [
                {"asset": "Growth ETF (VUG)", "allocation": "50%", "value": "$260,000", "return_ytd": "+18.5%"},
                {"asset": "Tech ETF (QQQ)", "allocation": "30%", "value": "$156,000", "return_ytd": "+22.1%"},
                {"asset": "Cash/Money Market", "allocation": "20%", "value": "$104,000", "return_ytd": "+4.5%"},
            ],
            "risk_profile": "Aggressive",
            "last_rebalanced": "2025-09-01",
        },
    }
    portfolio = portfolios.get(client_id)
    if portfolio is None:
        return json.dumps({"error": f"No portfolio found for client {client_id}"})
    return json.dumps({"portfolio": portfolio})


@tool(name="get_market_data", description="Get current market data for a specific asset or index.")
def get_market_data(
    symbol: Annotated[str, Field(description="Ticker symbol or index name (e.g., 'SPY', 'NASDAQ').")],
) -> str:
    """Get current market data including price, change, and key metrics."""
    market_data = {
        "SPY": {
            "symbol": "SPY",
            "name": "SPDR S&P 500 ETF",
            "price": "$542.30",
            "change": "+1.2%",
            "52w_high": "$560.00",
            "52w_low": "$420.50",
            "pe_ratio": 22.5,
            "dividend_yield": "1.3%",
        },
        "QQQ": {
            "symbol": "QQQ",
            "name": "Invesco QQQ Trust",
            "price": "$478.90",
            "change": "+1.8%",
            "52w_high": "$510.00",
            "52w_low": "$350.20",
            "pe_ratio": 30.2,
            "dividend_yield": "0.5%",
        },
        "BND": {
            "symbol": "BND",
            "name": "Vanguard Total Bond Market ETF",
            "price": "$72.15",
            "change": "-0.1%",
            "52w_high": "$75.00",
            "52w_low": "$68.50",
            "yield": "4.2%",
            "duration": "6.1 years",
        },
        "NASDAQ": {
            "symbol": "^IXIC",
            "name": "NASDAQ Composite",
            "price": "18,450.00",
            "change": "+1.5%",
            "52w_high": "19,200.00",
            "52w_low": "14,500.00",
        },
    }
    data = market_data.get(symbol.upper())
    if data is None:
        return json.dumps({"symbol": symbol, "error": f"No market data available for {symbol}"})
    return json.dumps({"market_data": data})


@tool(name="calculate_returns", description="Calculate projected investment returns.")
def calculate_returns(
    principal: Annotated[float, Field(description="Initial investment amount in USD.")],
    annual_rate: Annotated[float, Field(description="Expected annual return rate as a decimal (e.g., 0.07 for 7%).")],
    years: Annotated[int, Field(description="Investment time horizon in years.")],
) -> str:
    """Calculate projected returns with compound interest."""
    final_value = principal * ((1 + annual_rate) ** years)
    total_return = final_value - principal
    return json.dumps({
        "calculation": {
            "principal": f"${principal:,.2f}",
            "annual_rate": f"{annual_rate * 100:.1f}%",
            "years": years,
            "projected_value": f"${final_value:,.2f}",
            "total_return": f"${total_return:,.2f}",
            "total_return_pct": f"{(total_return / principal) * 100:.1f}%",
        }
    })


@tool(name="get_risk_assessment", description="Get a risk assessment for an investment strategy.")
def get_risk_assessment(
    risk_level: Annotated[str, Field(description="Risk tolerance level: 'conservative', 'moderate', or 'aggressive'.")],
) -> str:
    """Get recommended asset allocation and risk metrics based on risk tolerance."""
    assessments = {
        "conservative": {
            "risk_level": "Conservative",
            "recommended_allocation": {
                "bonds": "50%",
                "large_cap_stocks": "25%",
                "international": "10%",
                "cash": "15%",
            },
            "expected_annual_return": "4-6%",
            "max_drawdown_estimate": "-10% to -15%",
            "suitable_for": "Capital preservation, near-retirement, low risk tolerance",
            "rebalancing_frequency": "Annually",
        },
        "moderate": {
            "risk_level": "Moderate",
            "recommended_allocation": {
                "large_cap_stocks": "40%",
                "bonds": "25%",
                "international": "20%",
                "cash": "15%",
            },
            "expected_annual_return": "6-9%",
            "max_drawdown_estimate": "-20% to -30%",
            "suitable_for": "Balanced growth and income, medium-term goals",
            "rebalancing_frequency": "Semi-annually",
        },
        "aggressive": {
            "risk_level": "Aggressive",
            "recommended_allocation": {
                "growth_stocks": "50%",
                "tech_stocks": "25%",
                "international": "15%",
                "bonds": "5%",
                "cash": "5%",
            },
            "expected_annual_return": "10-15%",
            "max_drawdown_estimate": "-35% to -50%",
            "suitable_for": "Long-term growth, young investors, high risk tolerance",
            "rebalancing_frequency": "Quarterly",
        },
    }
    assessment = assessments.get(risk_level.lower())
    if assessment is None:
        return json.dumps({"error": f"Unknown risk level: {risk_level}. Use 'conservative', 'moderate', or 'aggressive'."})
    return json.dumps({"risk_assessment": assessment})


@tool(name="search_investment_options", description="Search for investment options by category.")
def search_investment_options(
    category: Annotated[str, Field(description="Investment category: 'etf', 'bonds', 'mutual_funds', or 'stocks'.")],
    risk_level: Annotated[str | None, Field(description="Optional risk filter: 'low', 'medium', 'high'.")] = None,
) -> str:
    """Search for investment options filtered by category and optional risk level."""
    options = {
        "etf": [
            {"name": "Vanguard S&P 500 ETF", "ticker": "VOO", "expense_ratio": "0.03%", "risk": "medium", "min_investment": "$1"},
            {"name": "iShares Core US Aggregate Bond", "ticker": "AGG", "expense_ratio": "0.03%", "risk": "low", "min_investment": "$1"},
            {"name": "ARK Innovation ETF", "ticker": "ARKK", "expense_ratio": "0.75%", "risk": "high", "min_investment": "$1"},
            {"name": "Vanguard Total International", "ticker": "VXUS", "expense_ratio": "0.07%", "risk": "medium", "min_investment": "$1"},
        ],
        "bonds": [
            {"name": "US Treasury 10-Year", "yield": "4.3%", "risk": "low", "maturity": "10 years"},
            {"name": "Corporate Bond Fund", "yield": "5.1%", "risk": "medium", "maturity": "5-7 years"},
            {"name": "High-Yield Bond ETF", "yield": "7.2%", "risk": "high", "maturity": "3-5 years"},
        ],
        "mutual_funds": [
            {"name": "Fidelity 500 Index", "ticker": "FXAIX", "expense_ratio": "0.015%", "risk": "medium", "min_investment": "$0"},
            {"name": "Vanguard Wellington", "ticker": "VWELX", "expense_ratio": "0.25%", "risk": "medium", "min_investment": "$3,000"},
            {"name": "T. Rowe Price Growth", "ticker": "PRGFX", "expense_ratio": "0.62%", "risk": "high", "min_investment": "$2,500"},
        ],
        "stocks": [
            {"name": "Note", "description": "Individual stock recommendations are not provided. Consider diversified ETFs or mutual funds instead."},
        ],
    }
    results = options.get(category.lower(), [])
    if risk_level:
        results = [opt for opt in results if opt.get("risk") == risk_level.lower()]
    return json.dumps({
        "category": category,
        "risk_filter": risk_level,
        "options_found": len(results),
        "options": results,
    })
