import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.market_data.yahoo_client import YahooFinanceClient

logger = logging.getLogger(__name__)


class BenchmarkEngine:
    """Evaluate the market-relative strength of portfolio holdings against a benchmark."""

    BENCHMARKS = {
        "NIFTY 50": "^NSEI",
        "NIFTY50": "^NSEI",
        "NIFTY 50 INDEX": "^NSEI",
        "NIFTY NEXT 50": "^NSE500",
        "NIFTY NEXT50": "^NSE500",
        "NIFTY NEXT 50 INDEX": "^NSE500",
        "NIFTY MIDCAP": "^NSEMDCP50",
        "NIFTY MIDCAP 50": "^NSEMDCP50",
        "MIDCAP": "^NSEMDCP50",
        "SENSEX": "^BSESN",
        "SENSEX 30": "^BSESN",
        "BSE SENSEX": "^BSESN",
    }
    THRESHOLDS = {
        "strong_outperformer": 5.0,
        "outperformer": 2.0,
        "underperformer": -2.0,
        "weak": -5.0,
    }
    RATING_THRESHOLDS = {
        "excellent": 15.0,
        "strong": 8.0,
        "good": 3.0,
        "neutral": -3.0,
        "weak": -8.0,
    }

    def __init__(
        self,
        yahoo_client: Optional[Any] = None,
        history_period: str = "2y",
        thresholds: Optional[Dict[str, float]] = None,
        rating_thresholds: Optional[Dict[str, float]] = None,
    ) -> None:
        self.yahoo_client = yahoo_client or YahooFinanceClient()
        self.history_period = history_period
        self.thresholds = thresholds or self.THRESHOLDS.copy()
        self.rating_thresholds = rating_thresholds or self.RATING_THRESHOLDS.copy()

    def compare_portfolio(
        self,
        portfolio_json: Dict[str, Any],
        benchmark_symbol: Optional[str] = None,
        lookback_period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compare portfolio holdings against a benchmark on a market-relative basis."""
        holdings = self._extract_holdings(portfolio_json)
        if not holdings:
            logger.warning("Portfolio comparison skipped because no holdings were supplied")
            return self._build_error_result("", "Portfolio does not contain any holdings.")

        resolved_symbol, benchmark_name = self._resolve_benchmark(portfolio_json, benchmark_symbol)
        if not resolved_symbol:
            logger.warning("Benchmark comparison skipped because no benchmark symbol was resolved")
            return self._build_error_result("", "Missing benchmark symbol.")

        logger.info("Benchmark resolution: %s (%s)", resolved_symbol, benchmark_name)

        normalized_period = "2y"
        benchmark_history = self._fetch_history(resolved_symbol, normalized_period)
        if benchmark_history.empty:
            logger.warning("Benchmark validation failed for %s", resolved_symbol)
            return self._build_error_result(resolved_symbol, f"Unable to fetch benchmark history for {resolved_symbol}.")

        benchmark_return_pct = self._calculate_return_pct(benchmark_history)
        if benchmark_return_pct is None:
            logger.warning("Benchmark return could not be calculated for %s", resolved_symbol)
            return self._build_error_result(resolved_symbol, f"Unable to calculate benchmark return for {resolved_symbol}.")

        logger.info("Benchmark return %.2f%% over %s", benchmark_return_pct, normalized_period)

        holding_results: List[Dict[str, Any]] = []
        for holding in holdings:
            symbol = self._extract_symbol(holding)
            if not symbol:
                logger.info("Skipping holding without a symbol")
                continue

            stock_history = self._fetch_history(symbol, normalized_period)
            if stock_history.empty:
                logger.warning("Skipping holding %s because no history was found", symbol)
                continue

            stock_return_pct = self._calculate_return_pct(stock_history)
            if stock_return_pct is None:
                logger.warning("Skipping holding %s because return data was invalid", symbol)
                continue

            relative_performance_pct = stock_return_pct - benchmark_return_pct
            classification = self._classify_relative_performance(relative_performance_pct)
            holding_results.append(
                {
                    "symbol": symbol,
                    "stock_name": self._extract_name(holding),
                    "stock_return_pct": round(float(stock_return_pct), 2),
                    "relative_performance_pct": round(float(relative_performance_pct), 2),
                    "classification": classification,
                }
            )

        if not holding_results:
            logger.warning("No valid holdings were available for benchmark comparison")
            return self._build_error_result(resolved_symbol, "No valid holdings were available for benchmark comparison.")

        analysed_symbols = {item["symbol"] for item in holding_results}
        weight_by_symbol = self._build_weight_lookup(holdings, analysed_symbols)
        weighted_results = self._build_weighted_results(holding_results, weight_by_symbol)
        weights = [entry[1] for entry in weighted_results]
        weighted_return_pct = self._calculate_weighted_return([entry[0] for entry in weighted_results], weights)
        portfolio_relative_performance_pct = self._calculate_weighted_relative_performance([entry[0] for entry in weighted_results], weights)
        portfolio_daily_returns, benchmark_daily_returns = self._build_portfolio_and_benchmark_return_series(
            holding_results, weight_by_symbol, benchmark_history
        )
        alpha_pct = self._calculate_alpha_pct(portfolio_daily_returns, benchmark_daily_returns)
        tracking_error_pct = self._calculate_tracking_error_pct(portfolio_daily_returns, benchmark_daily_returns)
        information_ratio = self._calculate_information_ratio(alpha_pct, tracking_error_pct)
        win_loss_ratio = self._calculate_win_loss_ratio(portfolio_daily_returns, benchmark_daily_returns)
        rolling_outperformance_pct = self._calculate_rolling_outperformance_pct(portfolio_daily_returns, benchmark_daily_returns)
        outperforming_holdings = sum(1 for item in holding_results if item["classification"] in {"Strong Outperformer", "Outperformer"})
        underperforming_holdings = sum(1 for item in holding_results if item["classification"] in {"Underperformer", "Weak"})
        ranked_results = self._rank_holdings(weighted_results)
        strongest_stock = ranked_results[0]["stock_name"] if ranked_results else None
        weakest_stock = ranked_results[-1]["stock_name"] if ranked_results else None
        overall_rating = self._classify_overall_rating(portfolio_relative_performance_pct)
        coverage = self._build_coverage_summary(holdings, holding_results)
        performance_summary = self._build_performance_summary(
            benchmark_name=benchmark_name,
            lookback_period=self._display_period(normalized_period),
            holdings=ranked_results,
            outperforming_holdings=outperforming_holdings,
            underperforming_holdings=underperforming_holdings,
            overall_rating=overall_rating,
            alpha_pct=alpha_pct,
            tracking_error_pct=tracking_error_pct,
            information_ratio=information_ratio,
            win_loss_ratio=win_loss_ratio,
            rolling_outperformance_pct=rolling_outperformance_pct,
        )

        logger.info(
            "Portfolio aggregation complete: analysed=%s, outperforming=%s, underperforming=%s, rating=%s",
            coverage["analysed_holdings"],
            outperforming_holdings,
            underperforming_holdings,
            overall_rating,
        )
        logger.info("Coverage statistics: %s", coverage)
        logger.info("Strongest holding: %s; weakest holding: %s", strongest_stock, weakest_stock)

        return {
            "benchmark": resolved_symbol,
            "benchmark_name": benchmark_name,
            "lookback_period": self._display_period(normalized_period),
            "benchmark_return_pct": round(float(benchmark_return_pct), 2),
            "portfolio_weighted_return_pct": round(float(weighted_return_pct), 2),
            "portfolio_relative_performance_pct": round(float(portfolio_relative_performance_pct), 2),
            "alpha_pct": alpha_pct,
            "tracking_error_pct": tracking_error_pct,
            "information_ratio": information_ratio,
            "win_loss_ratio": win_loss_ratio,
            "rolling_outperformance_pct": rolling_outperformance_pct,
            "outperforming_holdings": outperforming_holdings,
            "underperforming_holdings": underperforming_holdings,
            "strongest_stock": strongest_stock,
            "weakest_stock": weakest_stock,
            "overall_rating": overall_rating,
            "coverage": coverage,
            "performance_summary": performance_summary,
            "holdings": ranked_results,
            "error": None,
        }

    def _resolve_benchmark(self, portfolio_json: Dict[str, Any], benchmark_symbol: Optional[str]) -> Tuple[str, str]:
        """Resolve the benchmark symbol for the fixed portfolio schema."""
        return "^NSEI", "NIFTY 50"

    def _resolve_benchmark_name(self, benchmark_value: str) -> str:
        if not benchmark_value:
            return "NIFTY 50"
        normalized = benchmark_value.strip().lower()
        for name, symbol in self.BENCHMARKS.items():
            if normalized == name.lower() or normalized == symbol.lower():
                return name
        return benchmark_value

    def _resolve_benchmark_symbol(self, benchmark_value: str) -> str:
        if not benchmark_value:
            return "^NSEI"
        normalized = benchmark_value.strip().lower()
        for name, symbol in self.BENCHMARKS.items():
            if normalized == name.lower() or normalized == symbol.lower():
                return symbol
        return benchmark_value

    def _extract_holdings(self, portfolio_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        holdings = portfolio_json.get("holdings", [])
        return [holding for holding in holdings if isinstance(holding, dict)]

    def _extract_symbol(self, holding: Dict[str, Any]) -> Optional[str]:
        return str(holding["symbol"])

    def _extract_name(self, holding: Dict[str, Any]) -> str:
        return str(holding["stock_name"])

    def _build_weight_lookup(self, holdings: List[Dict[str, Any]], analysed_symbols: Optional[set] = None) -> Dict[str, float]:
        values_by_symbol: Dict[str, float] = {}
        analysed_symbol_set = analysed_symbols or set()
        for holding in holdings:
            symbol = self._extract_symbol(holding)
            if not symbol or (analysed_symbol_set and symbol not in analysed_symbol_set):
                continue
            value = self._coerce_numeric(holding["live_value"])
            if value is None:
                continue
            values_by_symbol[symbol] = values_by_symbol.get(symbol, 0.0) + float(value)
        return values_by_symbol

    def _build_weighted_results(self, holding_results: List[Dict[str, Any]], weight_lookup: Dict[str, float]) -> List[Tuple[Dict[str, Any], float]]:
        if not holding_results:
            return []

        total_value = sum(weight_lookup.values())
        if total_value <= 0:
            equal_weight = 1.0 / len(holding_results)
            return [(item, equal_weight) for item in holding_results]

        weighted_results: List[Tuple[Dict[str, Any], float]] = []
        for item in holding_results:
            symbol = item.get("symbol")
            weight_value = weight_lookup.get(symbol, 0.0)
            normalized_weight = (weight_value / total_value) if total_value > 0 else 0.0
            weighted_results.append((item, normalized_weight))
        return weighted_results

    def _calculate_weighted_return(self, holding_results: List[Dict[str, Any]], weights: List[float]) -> float:
        if not holding_results:
            return 0.0
        total_weight = sum(weights)
        if total_weight <= 0:
            return 0.0
        return sum((item["stock_return_pct"] * weight) for item, weight in zip(holding_results, weights)) / total_weight

    def _calculate_weighted_relative_performance(self, holding_results: List[Dict[str, Any]], weights: List[float]) -> float:
        if not holding_results:
            return 0.0
        total_weight = sum(weights)
        if total_weight <= 0:
            return 0.0
        return sum((item["relative_performance_pct"] * weight) for item, weight in zip(holding_results, weights)) / total_weight

    def _build_portfolio_and_benchmark_return_series(
        self,
        holding_results: List[Dict[str, Any]],
        weight_lookup: Dict[str, float],
        benchmark_history: pd.DataFrame,
    ) -> Tuple[pd.Series, pd.Series]:
        holding_returns: Dict[str, pd.Series] = {}
        for result in holding_results:
            symbol = result["symbol"]
            history = self._fetch_history(symbol, "2y")
            returns = self._build_daily_returns(history)
            if not returns.empty:
                holding_returns[symbol] = returns

        if not holding_returns or benchmark_history.empty:
            return pd.Series(dtype=float), pd.Series(dtype=float)

        benchmark_returns = self._build_daily_returns(benchmark_history).rename("benchmark")
        if benchmark_returns.empty:
            return pd.Series(dtype=float), pd.Series(dtype=float)

        aligned_frames = [benchmark_returns]
        for symbol, series in holding_returns.items():
            normalized_series = series.copy()
            normalized_index = pd.DatetimeIndex(normalized_series.index)
            if getattr(normalized_index, "tz", None) is not None:
                normalized_index = normalized_index.tz_localize(None)
            normalized_series.index = normalized_index
            aligned_frames.append(normalized_series.rename(symbol))

        aligned = pd.concat(aligned_frames, axis=1, join="inner").dropna()
        if aligned.empty:
            return pd.Series(dtype=float), pd.Series(dtype=float)

        weight_series = pd.Series({symbol: weight_lookup.get(symbol, 0.0) for symbol in aligned.columns if symbol != "benchmark"})
        if weight_series.empty or weight_series.sum() <= 0:
            return pd.Series(dtype=float), benchmark_returns.loc[aligned.index]
        weight_series = weight_series / weight_series.sum()
        portfolio_returns = aligned[[symbol for symbol in weight_series.index]].mul(weight_series, axis=1).sum(axis=1)
        return portfolio_returns, benchmark_returns.loc[aligned.index]

    def _build_daily_returns(self, history: pd.DataFrame) -> pd.Series:
        if history.empty:
            return pd.Series(dtype=float)
        close_col = "Adj Close" if "Adj Close" in history.columns else "Close"
        if close_col not in history.columns:
            return pd.Series(dtype=float)
        price_series = pd.to_numeric(history[close_col], errors="coerce").dropna()
        if price_series.empty:
            return pd.Series(dtype=float)
        returns = price_series.pct_change().dropna()
        returns.index = pd.to_datetime(returns.index)
        if getattr(returns.index, "tz", None) is not None:
            returns.index = returns.index.tz_localize(None)
        return returns

    def _calculate_alpha_pct(self, portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> Optional[float]:
        if portfolio_returns.empty or benchmark_returns.empty:
            return None
        excess = portfolio_returns.sub(benchmark_returns, fill_value=0.0).dropna()
        if excess.empty:
            return None
        annualized_excess = float(excess.mean()) * 252.0 * 100.0
        return round(annualized_excess, 2)

    def _calculate_tracking_error_pct(self, portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> Optional[float]:
        if portfolio_returns.empty or benchmark_returns.empty:
            return None
        excess = portfolio_returns.sub(benchmark_returns, fill_value=0.0).dropna()
        if excess.empty:
            return None
        std_excess = float(excess.std(ddof=1))
        return round(std_excess * np.sqrt(252.0) * 100.0, 2)

    def _calculate_information_ratio(self, alpha_pct: Optional[float], tracking_error_pct: Optional[float]) -> Optional[float]:
        if alpha_pct is None or tracking_error_pct is None or tracking_error_pct == 0.0:
            return None
        return round(alpha_pct / tracking_error_pct, 2)

    def _calculate_win_loss_ratio(self, portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> Optional[float]:
        if portfolio_returns.empty or benchmark_returns.empty:
            return None
        excess = portfolio_returns.sub(benchmark_returns, fill_value=0.0).dropna()
        out = int((excess > 0).sum())
        under = int((excess < 0).sum())
        if out == 0 and under == 0:
            return None
        if under == 0:
            return float(out)
        return round(out / under, 2)

    def _calculate_rolling_outperformance_pct(self, portfolio_returns: pd.Series, benchmark_returns: pd.Series, window: int = 30) -> Optional[float]:
        if portfolio_returns.empty or benchmark_returns.empty:
            return None
        excess = portfolio_returns.sub(benchmark_returns, fill_value=0.0).dropna()
        if len(excess) < 2:
            return None
        window = min(window, len(excess))
        rolling = excess.rolling(window).mean().dropna()
        if rolling.empty:
            return None
        return round(float(rolling.iloc[-1] * 100.0), 2)

    def _classify_relative_performance(self, relative_performance_pct: float) -> str:
        if relative_performance_pct >= self.thresholds["strong_outperformer"]:
            return "Strong Outperformer"
        if relative_performance_pct >= self.thresholds["outperformer"]:
            return "Outperformer"
        if relative_performance_pct <= self.thresholds["weak"]:
            return "Weak"
        if relative_performance_pct <= self.thresholds["underperformer"]:
            return "Underperformer"
        return "Neutral"

    def _classify_overall_rating(self, portfolio_relative_performance_pct: float) -> str:
        if portfolio_relative_performance_pct >= self.rating_thresholds["excellent"]:
            return "Excellent"
        if portfolio_relative_performance_pct >= self.rating_thresholds["strong"]:
            return "Strong"
        if portfolio_relative_performance_pct >= self.rating_thresholds["good"]:
            return "Good"
        if portfolio_relative_performance_pct > self.rating_thresholds["neutral"]:
            return "Neutral"
        if portfolio_relative_performance_pct >= self.rating_thresholds["weak"]:
            return "Weak"
        return "Poor"

    def _rank_holdings(self, weighted_results: List[Tuple[Dict[str, Any], float]]) -> List[Dict[str, Any]]:
        ranked_results = []
        for index, (item, weight) in enumerate(sorted(weighted_results, key=lambda entry: entry[0]["relative_performance_pct"], reverse=True), start=1):
            item_copy = dict(item)
            item_copy["rank"] = index
            item_copy["relative_performance_contribution_pct"] = round(float(weight * item_copy["relative_performance_pct"]), 2)
            ranked_results.append(item_copy)
        return ranked_results

    def _build_coverage_summary(self, holdings: List[Dict[str, Any]], holding_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_holdings = len(holdings)
        analysed_holdings = len(holding_results)
        failed_holdings = total_holdings - analysed_holdings
        coverage_pct = round((analysed_holdings / total_holdings) * 100.0, 1) if total_holdings else 100.0
        return {
            "total_holdings": total_holdings,
            "analysed_holdings": analysed_holdings,
            "failed_holdings": failed_holdings,
            "coverage_pct": coverage_pct,
        }

    def _build_performance_summary(
        self,
        benchmark_name: str,
        lookback_period: str,
        holdings: List[Dict[str, Any]],
        outperforming_holdings: int,
        underperforming_holdings: int,
        overall_rating: str,
        alpha_pct: Optional[float] = None,
        tracking_error_pct: Optional[float] = None,
        information_ratio: Optional[float] = None,
        win_loss_ratio: Optional[float] = None,
        rolling_outperformance_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        summary = {
            "benchmark": benchmark_name,
            "lookback_period": lookback_period,
            "stocks_analysed": len(holdings),
            "stocks_outperforming": outperforming_holdings,
            "stocks_underperforming": underperforming_holdings,
            "portfolio_strength": overall_rating,
        }
        if alpha_pct is not None:
            summary["alpha_pct"] = alpha_pct
        if tracking_error_pct is not None:
            summary["tracking_error_pct"] = tracking_error_pct
        if information_ratio is not None:
            summary["information_ratio"] = information_ratio
        if win_loss_ratio is not None:
            summary["win_loss_ratio"] = win_loss_ratio
        if rolling_outperformance_pct is not None:
            summary["rolling_outperformance_pct"] = rolling_outperformance_pct
        return summary

    def _fetch_history(self, symbol: str, period: str) -> pd.DataFrame:
        """Fetch normalized historical prices for a benchmark or stock symbol."""
        try:
            history = self.yahoo_client.get_historical_prices(symbol, period=period)
        except TypeError:
            history = self.yahoo_client.get_historical_prices(symbol)

        if not isinstance(history, pd.DataFrame):
            return pd.DataFrame()
        return self._prepare_history(history)

    def _prepare_history(self, history: pd.DataFrame) -> pd.DataFrame:
        """Normalize benchmark history into a frame with a date column and price column."""
        if history.empty:
            return history

        prepared = history.copy()
        if "Date" not in prepared.columns and prepared.index.name is not None:
            prepared = prepared.reset_index()

        if "Date" in prepared.columns:
            prepared["Date"] = pd.to_datetime(prepared["Date"], errors="coerce")
            prepared = prepared.dropna(subset=["Date"]).sort_values("Date")
        elif isinstance(prepared.index, pd.DatetimeIndex):
            prepared = prepared.reset_index()
            prepared.columns = ["Date" if column == "index" else column for column in prepared.columns]

        return prepared

    def _calculate_return_pct(self, prices: pd.DataFrame) -> Optional[float]:
        """Calculate percentage return from the first and last adjusted close prices."""
        if prices.empty:
            return None
        
        close_column = "Adj Close" if "Adj Close" in prices.columns else "Close"
        if close_column not in prices.columns:
            return None

        close_series = pd.to_numeric(prices[close_column], errors="coerce")
        close_series = close_series.dropna()
        if close_series.empty:
            return None

        first_price = close_series.iloc[0]
        last_price = close_series.iloc[-1]
        if pd.isna(first_price) or pd.isna(last_price) or first_price == 0:
            return None

        return ((last_price - first_price) / first_price) * 100.0

    def _normalize_period(self, period: Optional[str]) -> str:
        if not period:
            return self.history_period
        normalized = str(period).strip().lower()
        if normalized.endswith("mo"):
            return normalized
        if normalized.endswith("m"):
            return f"{normalized[:-1]}mo"
        if normalized.endswith("y"):
            return normalized
        if normalized.endswith("yr"):
            return normalized[:-2] + "y"
        return normalized

    def _display_period(self, period: str) -> str:
        normalized = str(period).strip().lower()
        if normalized.endswith("mo"):
            return normalized[:-2].upper() + "M"
        if normalized.endswith("y"):
            return normalized[:-1].upper() + "Y"
        return normalized.upper()

    def _coerce_numeric(self, value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _extract_string(self, payload: Dict[str, Any], keys: List[str]) -> Optional[str]:
        if not isinstance(payload, dict):
            return None
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict):
                return None
            if key not in current:
                return None
            current = current[key]
        if current is None:
            return None
        return str(current)

    def _build_error_result(self, benchmark_symbol: str, message: str) -> Dict[str, Any]:
        return {
            "benchmark": benchmark_symbol,
            "benchmark_name": "NIFTY 50",
            "lookback_period": self._display_period(self.history_period),
            "benchmark_return_pct": None,
            "portfolio_weighted_return_pct": None,
            "portfolio_relative_performance_pct": None,
            "outperforming_holdings": None,
            "underperforming_holdings": None,
            "strongest_stock": None,
            "weakest_stock": None,
            "overall_rating": None,
            "coverage": {
                "total_holdings": 0,
                "analysed_holdings": 0,
                "failed_holdings": 0,
                "coverage_pct": 0.0,
            },
            "performance_summary": {
                "benchmark": "NIFTY 50",
                "lookback_period": self._display_period(self.history_period),
                "stocks_analysed": 0,
                "stocks_outperforming": 0,
                "stocks_underperforming": 0,
                "portfolio_strength": "Neutral",
            },
            "holdings": [],
            "error": message,
        }
