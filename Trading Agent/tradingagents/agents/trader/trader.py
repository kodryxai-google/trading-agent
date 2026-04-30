"""Trader: turns the Research Manager's investment plan into a concrete transaction proposal."""

from __future__ import annotations

import functools

from langchain_core.messages import AIMessage

from tradingagents.agents.schemas import TraderProposal, render_trader_proposal
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_professional_rules
from tradingagents.agents.utils.confidence import (
    infer_factors_from_reports,
    compute_confidence,
)
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_trader(llm):
    structured_llm = bind_structured(llm, TraderProposal, "Trader")

    def trader_node(state, name):
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(company_name)
        investment_plan = state["investment_plan"]

        # Infer confidence from analyst reports available in state
        factors = infer_factors_from_reports(
            market_report=state.get("market_report", ""),
            news_report=state.get("news_report", ""),
            fundamentals_report=state.get("fundamentals_report", ""),
            anomaly_flags=state.get("data_anomalies", []),
        )
        confidence = compute_confidence(factors)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a professional institutional equity trader. "
                    "Based on the research plan, provide a concrete transaction recommendation. "
                    "Anchor your reasoning in the analysts' reports and the research plan. "
                    f"Set confidence_score to {confidence} reflecting the signal quality. "
                    + get_professional_rules()
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Based on a comprehensive analysis by a team of analysts, here is an investment "
                    f"plan tailored for {company_name}. {instrument_context} This plan incorporates "
                    f"insights from current technical market trends, macroeconomic indicators, and "
                    f"social media sentiment. Use this plan as a foundation for evaluating your next "
                    f"trading decision.\n\nProposed Investment Plan: {investment_plan}\n\n"
                    f"Leverage these insights to make an informed and strategic decision. "
                    f"Your confidence_score should be {confidence}."
                ),
            },
        ]

        trader_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            messages,
            render_trader_proposal,
            "Trader",
        )

        return {
            "messages": [AIMessage(content=trader_plan)],
            "trader_investment_plan": trader_plan,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
