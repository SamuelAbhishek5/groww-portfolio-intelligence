import pandas as pd

from backend.analytics.holding_risk_engine import HoldingRiskEngine
from backend.analytics.risk_engine import RiskEngine


def test_holding_analysis_returns_expected_structure():
    holdings_df = pd.DataFrame(
        [
            {
                "symbol": "AAPL",
                "stock_name": "Apple Inc.",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "live_value": 500.0,
            },
            {
                "symbol": "MSFT",
                "stock_name": "Microsoft Corp.",
                "sector": "Technology",
                "industry": "Software",
                "live_value": 500.0,
            },
        ]
    )
    returns_df = pd.DataFrame(
        {
            "AAPL": [0.01, -0.02, 0.03, 0.01],
            "MSFT": [0.02, 0.01, -0.01, 0.02],
        }
    )
    benchmark_returns = pd.Series([0.015, -0.015, 0.02, 0.015], name="^NSEI")
    weights = pd.Series([0.5, 0.5], index=["AAPL", "MSFT"])

    engine = RiskEngine(benchmark_symbol="^NSEI", history_period="1mo")
    holding_engine = HoldingRiskEngine(
        normalized_holdings=holdings_df,
        returns_df=returns_df,
        benchmark_returns=benchmark_returns,
        portfolio_weights=weights,
        covariance_matrix=returns_df.cov(),
        risk_engine=engine,
        risk_free_rate=0.02,
    )

    holding_analysis, holding_summary = holding_engine.build_analysis()

    assert len(holding_analysis) == 2
    first_item = holding_analysis[0]
    assert first_item["symbol"] in {"AAPL", "MSFT"}
    assert "weight_pct" in first_item
    assert "risk_score" in first_item
    assert "risk_level" in first_item
    assert "performance_contribution_pct" in first_item
    assert "diversification_score" in first_item

    assert set(holding_summary.keys()) == {
        "highest_risk_stock",
        "lowest_risk_stock",
        "largest_risk_contributor",
        "largest_return_contributor",
        "worst_performing_stock",
        "best_performing_stock",
        "best_diversifier",
        "worst_diversifier",
    }
