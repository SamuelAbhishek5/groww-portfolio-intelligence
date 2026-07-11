from backend.analytics.portfolio_health import PortfolioHealthEngine


def test_calculate_health_returns_expected_structure():
    portfolio_json = {
        "portfolio": {
            "num_holdings": 2,
            "total_portfolio_value": 100000.0,
        },
        "portfolio_summary": {
            "total_invested_value": 100000.0,
            "total_live_value": 112000.0,
        },
        "risk_summary": {
            "risk_score": 42.0,
            "sharpe_ratio": 0.8,
            "max_drawdown": {"percent": 18.0},
            "volatility": {"value_pct": 12.0},
        },
        "diversification": {"score": 88.0},
        "concentration_risk": {"top_holding_weight_pct": 35.0, "hhi": 0.3},
        "holdings": [
            {
                "symbol": "RELIANCE.NS",
                "stock_name": "Reliance",
                "market_cap": 15000000000000,
                "pe_ratio": 20.0,
                "dividend_yield": 2.0,
                "beta": 0.95,
                "sharpe": 1.2,
            },
            {
                "symbol": "ITC.NS",
                "stock_name": "ITC",
                "market_cap": 5000000000000,
                "pe_ratio": 18.0,
                "dividend_yield": 3.5,
                "beta": 1.1,
                "sharpe": 0.4,
            },
        ],
    }

    engine = PortfolioHealthEngine()
    result = engine.calculate_health(portfolio_json)

    assert set(result.keys()) == {"portfolio_health"}
    health = result["portfolio_health"]
    assert 0 <= health["overall_score"] <= 100
    assert health["grade"] in {"A+", "A", "B", "C", "D", "F"}
    assert health["status"]
    assert set(health["breakdown"].keys()) == {
        "risk",
        "diversification",
        "performance",
        "concentration",
        "quality",
        "stability",
    }
    assert set(health["weighted_scores"].keys()) == {
        "risk",
        "diversification",
        "performance",
        "concentration",
        "quality",
        "stability",
    }
    assert isinstance(health["strengths"], list)
    assert isinstance(health["weaknesses"], list)
    assert isinstance(health["recommendations"], list)
    assert isinstance(health["summary"], str)


def test_calculate_health_penalizes_high_concentration_and_negative_sharpe():
    portfolio_json = {
        "portfolio": {"num_holdings": 2, "total_portfolio_value": 100000.0},
        "portfolio_summary": {"total_invested_value": 100000.0, "total_live_value": 90000.0},
        "risk_summary": {
            "risk_score": 65.0,
            "sharpe_ratio": -1.07,
            "max_drawdown": {"percent": 22.0},
            "volatility": {"value_pct": 28.0},
        },
        "diversification": {"score": 40.0},
        "concentration_risk": {"top_holding_weight_pct": 52.5, "hhi": 0.52, "effective_holdings": 1.9},
        "holdings": [
            {
                "symbol": "AAA.NS",
                "stock_name": "AAA",
                "market_cap": 30000000000,
                "pe_ratio": 18.0,
                "dividend_yield": 1.2,
                "beta": 1.1,
                "sharpe": -0.8,
            },
            {
                "symbol": "BBB.NS",
                "stock_name": "BBB",
                "market_cap": 25000000000,
                "pe_ratio": 25.0,
                "dividend_yield": 0.8,
                "beta": 0.9,
                "sharpe": 0.5,
            },
        ],
    }
    benchmark_metrics = {
        "portfolio_relative_performance_pct": -19.0,
        "benchmark_return_pct": 10.0,
        "portfolio_weighted_return_pct": -9.0,
    }

    engine = PortfolioHealthEngine()
    result = engine.calculate_health(portfolio_json, benchmark_metrics=benchmark_metrics)
    health = result["portfolio_health"]

    assert health["status"] in {"Fair", "Average", "Needs Improvement", "Poor"}
    assert health["grade"] in {"B", "C", "D", "F"}
    assert health["breakdown"]["concentration"] < 60.0
    assert "underperformed the benchmark" in " ".join(health["weaknesses"]).lower()
    assert "negative risk-adjusted returns" in " ".join(health["weaknesses"]).lower()
