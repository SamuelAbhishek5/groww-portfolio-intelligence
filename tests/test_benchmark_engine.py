import pandas as pd

from backend.analytics.benchmark_engine import BenchmarkEngine


class DummyYahooClient:
    def __init__(self, history_map=None, benchmark_error=False):
        self.history_map = history_map or {}
        self.benchmark_error = benchmark_error

    def get_historical_prices(self, symbol: str, period: str = "2y", start_date=None, end_date=None):
        if self.benchmark_error and symbol.startswith("^"):
            return pd.DataFrame()
        if symbol in self.history_map:
            return self.history_map[symbol]
        return pd.DataFrame()


def test_benchmark_resolution_and_relative_performance():
    history_map = {
        "^NSEI": pd.DataFrame({"Adj Close": [100.0, 110.0]}, index=pd.to_datetime(["2024-01-01", "2024-12-31"])),
        "RELIANCE.NS": pd.DataFrame({"Adj Close": [100.0, 125.0]}, index=pd.to_datetime(["2024-01-01", "2024-12-31"])),
        "ITC.NS": pd.DataFrame({"Adj Close": [100.0, 105.0]}, index=pd.to_datetime(["2024-01-01", "2024-12-31"])),
    }
    engine = BenchmarkEngine(yahoo_client=DummyYahooClient(history_map=history_map))
    portfolio_json = {
        "benchmark": "NIFTY 50",
        "holdings": [
            {"symbol": "RELIANCE.NS", "stock_name": "Reliance", "live_value": 200.0},
            {"symbol": "ITC.NS", "stock_name": "ITC", "live_value": 100.0},
        ],
    }

    result = engine.compare_portfolio(portfolio_json)

    assert result["benchmark"] == "^NSEI"
    assert result["benchmark_name"] == "NIFTY 50"
    assert result["benchmark_return_pct"] == 10.0
    assert result["holdings"][0]["classification"] == "Strong Outperformer"
    assert "benchmark_return_pct" not in result["holdings"][0]
    assert result["portfolio_weighted_return_pct"] == 18.33
    assert result["portfolio_relative_performance_pct"] == 8.33
    assert result["overall_rating"] == "Strong"
    assert result["outperforming_holdings"] == 1
    assert result["underperforming_holdings"] == 1
    assert result["holdings"][0]["rank"] == 1
    assert result["holdings"][1]["rank"] == 2
    assert result["coverage"]["coverage_pct"] == 100.0
    assert result["performance_summary"]["portfolio_strength"] == "Strong"


def test_benchmark_fetch_failure_returns_error_message():
    engine = BenchmarkEngine(yahoo_client=DummyYahooClient(benchmark_error=True))
    portfolio_json = {"holdings": [{"symbol": "RELIANCE.NS", "live_value": 100.0}]}

    result = engine.compare_portfolio(portfolio_json)

    assert result["error"] == "Unable to fetch benchmark history for ^NSEI."


def test_invalid_symbols_are_skipped():
    history_map = {
        "^NSEI": pd.DataFrame({"Adj Close": [100.0, 110.0]}, index=pd.to_datetime(["2024-01-01", "2024-12-31"])),
        "RELIANCE.NS": pd.DataFrame({"Adj Close": [100.0, 120.0]}, index=pd.to_datetime(["2024-01-01", "2024-12-31"])),
    }
    engine = BenchmarkEngine(yahoo_client=DummyYahooClient(history_map=history_map))
    portfolio_json = {"holdings": [{"symbol": "INVALID", "live_value": 100.0}, {"symbol": "RELIANCE.NS", "live_value": 100.0}]}

    result = engine.compare_portfolio(portfolio_json)

    assert len(result["holdings"]) == 1
    assert result["holdings"][0]["symbol"] == "RELIANCE.NS"


def test_empty_portfolio_returns_error():
    engine = BenchmarkEngine(yahoo_client=DummyYahooClient())

    result = engine.compare_portfolio({"holdings": []})

    assert result["error"] == "Portfolio does not contain any holdings."


def test_skipped_holdings_do_not_distort_weights():
    history_map = {
        "^NSEI": pd.DataFrame({"Adj Close": [100.0, 110.0]}, index=pd.to_datetime(["2024-01-01", "2024-12-31"])),
        "RELIANCE.NS": pd.DataFrame({"Adj Close": [100.0, 120.0]}, index=pd.to_datetime(["2024-01-01", "2024-12-31"])),
    }
    engine = BenchmarkEngine(yahoo_client=DummyYahooClient(history_map=history_map))
    portfolio_json = {
        "holdings": [
            {"symbol": "RELIANCE.NS", "stock_name": "Reliance", "live_value": 200.0},
            {"symbol": "ITC.NS", "stock_name": "ITC", "live_value": 100.0},
        ]
    }

    result = engine.compare_portfolio(portfolio_json, benchmark_symbol="^NSEI")

    assert len(result["holdings"]) == 1
    assert result["portfolio_weighted_return_pct"] == 20.0
    assert result["portfolio_relative_performance_pct"] == 10.0


def test_classification_thresholds_and_weighted_aggregation():
    history_map = {
        "^NSEI": pd.DataFrame({"Adj Close": [100.0, 110.0]}, index=pd.to_datetime(["2024-01-01", "2024-12-31"])),
        "RELIANCE.NS": pd.DataFrame({"Adj Close": [100.0, 110.0]}, index=pd.to_datetime(["2024-01-01", "2024-12-31"])),
        "ITC.NS": pd.DataFrame({"Adj Close": [100.0, 90.0]}, index=pd.to_datetime(["2024-01-01", "2024-12-31"])),
    }
    engine = BenchmarkEngine(yahoo_client=DummyYahooClient(history_map=history_map))
    portfolio_json = {
        "holdings": [
            {"symbol": "RELIANCE.NS", "stock_name": "Reliance", "live_value": 100.0},
            {"symbol": "ITC.NS", "stock_name": "ITC", "live_value": 100.0},
        ]
    }

    result = engine.compare_portfolio(portfolio_json, benchmark_symbol="^NSEI")

    assert result["holdings"][0]["classification"] == "Neutral"
    assert result["holdings"][1]["classification"] == "Weak"
    assert result["portfolio_relative_performance_pct"] == -10.0
    assert result["overall_rating"] == "Poor"
    assert result["strongest_stock"] == "Reliance"
    assert result["weakest_stock"] == "ITC"
    assert result["coverage"]["failed_holdings"] == 0
    assert result["performance_summary"]["stocks_underperforming"] == 1
