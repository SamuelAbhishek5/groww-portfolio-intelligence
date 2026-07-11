import pytest

from backend.ai.ai_insight_engine import AIInsightEngine
from backend.ai.insight_formatter import InsightFormatter
from backend.ai.prompt_builder import PromptBuilder
from backend.ai.response_parser import ResponseParser


@pytest.fixture
def sample_inputs():
    portfolio_json = {
        "summary": {
            "total_invested_value": 1000000,
            "total_live_value": 1080000,
            "total_unrealised_pnl": 80000,
        },
        "holdings": [
            {"symbol": "RELIANCE", "company_name": "Reliance Industries", "sector": "Energy", "live_value": 500000},
            {"symbol": "TCS", "company_name": "Tata Consultancy Services", "sector": "IT", "live_value": 300000},
            {"symbol": "HDFCBANK", "company_name": "HDFC Bank", "sector": "Banking", "live_value": 200000},
        ],
    }
    risk_metrics = {
        "risk_score": 72,
        "summary": {
            "annualized_volatility": 0.24,
            "portfolio_beta": 1.1,
            "var_95": 0.03,
            "expected_shortfall_95": 0.04,
            "max_drawdown": 0.18,
            "sharpe_ratio": 0.8,
            "diversification_score": 0.62,
        },
        "risk_contributions": {"RELIANCE": 0.55, "TCS": 0.25},
        "concentration_risk": {"top_holding_weight_pct": 42.0, "effective_holdings": 3.0},
    }
    health_metrics = {
        "portfolio_health": {
            "overall_score": 74,
            "grade": "B",
            "status": "Stable",
            "strengths": ["Balanced sector mix"],
            "weaknesses": ["Top holding remains large"],
            "summary": "Portfolio quality is acceptable.",
        }
    }
    benchmark_metrics = {
        "benchmark_return_pct": 8.5,
        "portfolio_weighted_return_pct": 10.2,
        "portfolio_relative_performance_pct": 1.7,
        "strongest_stock": "RELIANCE",
        "weakest_stock": "HDFCBANK",
        "outperforming_holdings": 2,
    }
    opportunity_result = {
        "summary": "The portfolio shows moderate concentration and room to improve sector breadth.",
        "strengths": [{"title": "Strong return profile"}],
        "risks": [{"title": "Single-stock concentration"}],
        "opportunities": [{"title": "Broaden sector exposure"}],
        "action_plan": [{"title": "Trim the largest holding"}],
    }

    return {
        "portfolio_json": portfolio_json,
        "risk_metrics": risk_metrics,
        "health_metrics": health_metrics,
        "benchmark_metrics": benchmark_metrics,
        "opportunity_result": opportunity_result,
    }


def test_prompt_builder_creates_compact_markdown_prompt(sample_inputs):
    prompt = PromptBuilder().build_prompt(**sample_inputs)

    assert "Portfolio Overview" in prompt
    assert "Risk Summary" in prompt
    assert "Health Summary" in prompt
    assert "Benchmark Summary" in prompt
    assert "Portfolio Opportunities" in prompt
    assert "RELIANCE" in prompt


def test_prompt_builder_includes_strict_metric_and_formatting_guidance(sample_inputs):
    prompt = PromptBuilder().build_prompt(**sample_inputs)

    assert "No LaTeX" in prompt
    assert "Absolute Portfolio Return" in prompt
    assert "Annualized Portfolio Return" in prompt
    assert "Portfolio Health Metrics" in prompt
    assert "tracking_error" in prompt
    assert "information_ratio" in prompt


def test_response_parser_recovers_from_invalid_payload():
    parser = ResponseParser()
    parsed, errors = parser.parse_and_validate('{"executive_summary": 123, "strengths": "bad"}')

    assert parsed["executive_summary"]
    assert errors
    assert parsed["strengths"] == []


def test_formatter_normalizes_output_payload():
    formatter = InsightFormatter()
    payload = {
        "executive_summary": "A steady portfolio.",
        "portfolio_story": "Performance is improving.",
        "strengths": ["Quality holdings"],
        "weaknesses": ["High concentration"],
        "risk_commentary": "Risk remains manageable.",
        "performance_commentary": "Returns are positive.",
        "benchmark_commentary": "Outperformed benchmark.",
        "diversification_commentary": "Diversification is adequate.",
        "holding_insights": [{"symbol": "RELIANCE", "company": "Reliance", "analysis": "Solid", "strengths": ["Large franchise"], "risks": ["Concentration"], "recommendation": "Monitor"}],
        "sector_insights": [{"sector": "Energy", "analysis": "Core exposure", "recommendation": "Maintain"}],
        "priority_actions": [{"priority": "High", "title": "Trim", "reason": "Reduce risk"}],
        "future_outlook": "Stay disciplined.",
        "investor_profile": {"type": "Balanced", "confidence": 0.8, "reason": "Risk profile fits"},
    }

    normalized = formatter.format(payload)

    assert normalized["executive_summary"] == "A steady portfolio."
    assert normalized["holding_insights"][0]["symbol"] == "RELIANCE"
    assert normalized["investor_profile"]["confidence"] == 0.8


def test_response_parser_strips_markdown_code_fences():
    parser = ResponseParser()
    parsed, errors = parser.parse_and_validate("```json\n{\"executive_summary\": \"Trimmed\", \"portfolio_story\": \"Story\", \"strengths\": [], \"weaknesses\": [], \"risk_commentary\": \"Risk\", \"performance_commentary\": \"Perf\", \"benchmark_commentary\": \"Bench\", \"diversification_commentary\": \"Div\", \"holding_insights\": [], \"sector_insights\": [], \"priority_actions\": [], \"future_outlook\": \"Out\", \"investor_profile\": {\"type\": \"Balanced\", \"confidence\": 0.7, \"reason\": \"Reason\"}}\n```")

    assert parsed["executive_summary"] == "Trimmed"
    assert errors == []


def test_engine_returns_data_driven_fallback_when_llm_is_unavailable(sample_inputs):
    class FailingLLMClient:
        def generate(self, prompt, system_prompt=None, timeout=None):
            raise RuntimeError("LLM unavailable")

    engine = AIInsightEngine(llm_client=FailingLLMClient())
    result = engine.generate_insights(**sample_inputs)

    assert "positive" in result["executive_summary"].lower() or "risk" in result["executive_summary"].lower()
    assert result["priority_actions"]
    assert result["investor_profile"]["type"]


def test_engine_returns_fallback_when_llm_is_unavailable(sample_inputs):
    class FailingLLMClient:
        def generate(self, prompt, system_prompt=None, timeout=None):
            raise RuntimeError("LLM unavailable")

    engine = AIInsightEngine(llm_client=FailingLLMClient())
    result = engine.generate_insights(**sample_inputs)

    assert result["executive_summary"]
    assert result["strengths"]
    assert result["priority_actions"]
    assert result["investor_profile"]["type"]
