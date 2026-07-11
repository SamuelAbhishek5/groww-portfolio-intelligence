from backend.analytics.opportunity_engine import OpportunityEngine


def test_opportunity_engine_returns_structured_ai_input():
    portfolio_json = {
        "holdings": [
            {
                "symbol": "RELIANCE.NS",
                "stock_name": "Reliance Industries",
                "sector": "Energy",
                "pe_ratio": 21.66611,
                "dividend_yield": 0.46,
                "live_value": 12939.0,
            },
            {
                "symbol": "ITC.NS",
                "stock_name": "ITC Ltd",
                "sector": "Consumer Defensive",
                "pe_ratio": 17.380377,
                "dividend_yield": 5.5,
                "live_value": 14347.5,
            },
        ]
    }
    risk_metrics = {
        "risk_summary": {
            "risk_score": 42.34,
            "portfolio_beta": 0.8083329760732885,
            "sharpe_ratio": -1.1010440906627956,
            "daily_var": {"percent": 1.65},
            "max_drawdown": {"percent": 28.85},
        },
        "concentration_risk": {
            "top_holding_weight_pct": 52.58,
            "hhi": 0.501332,
            "effective_holdings": 1.99,
        },
        "diversification": {"score": 87.82},
        "correlation": {"average": 0.3006},
        "risk_contributions": {"ITC.NS": 0.5025, "RELIANCE.NS": 0.4975},
        "stress_test": {"market_selloff": {"portfolio_return_pct": -10.0}},
        "holding_analysis": [
            {"symbol": "RELIANCE.NS", "company": "Reliance Industries", "weight_pct": 47.42},
            {"symbol": "ITC.NS", "company": "ITC Ltd", "weight_pct": 52.58},
        ],
        "holding_summary": {"worst_performing_stock": "ITC.NS"},
    }
    benchmark_metrics = {
        "portfolio_relative_performance_pct": -19.43,
        "portfolio_weighted_return_pct": -20.58,
        "weakest_stock": "ITC Ltd",
        "overall_rating": "Poor",
        "performance_summary": {"portfolio_strength": "Poor"},
    }

    result = OpportunityEngine().analyze(portfolio_json, risk_metrics, benchmark_metrics)

    assert set(result.keys()) == {"summary", "strengths", "risks", "opportunities", "action_plan"}
    assert result["summary"]["overall_status"] == "High Improvement Potential"
    assert result["summary"]["risk_count"] >= 1
    assert result["summary"]["opportunity_count"] >= 1
    assert result["summary"]["action_count"] >= 1
    assert result["summary"]["highest_priority_issue"]
    assert result["summary"]["key_strength"]
    assert result["summary"]["top_recommendation"]
    assert result["summary"]["finding_counts"]["actions"] >= 1

    risk_priorities = [item["priority"] for item in result["risks"]]
    assert risk_priorities == sorted(risk_priorities)

    first_risk = result["risks"][0]
    assert {"id", "theme", "category", "severity", "priority", "title", "reason", "recommendation", "expected_benefit", "metric", "related_symbols"} <= set(first_risk)

    first_action = result["action_plan"][0]
    assert {"priority", "title", "action", "expected_benefit"} <= set(first_action)
    assert len(result["action_plan"]) <= 5
