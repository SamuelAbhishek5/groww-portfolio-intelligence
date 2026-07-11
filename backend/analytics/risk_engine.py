import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import yfinance as yf
from backend.analytics.holding_risk_engine import HoldingRiskEngine
from backend.market_data.yahoo_client import YahooFinanceClient
from backend.analytics.portfolio_health import PortfolioHealthEngine

logger = logging.getLogger(__name__)

DEFAULT_BENCHMARK = "^NSEI"
DEFAULT_HISTORY_PERIOD = "2y"
DEFAULT_ANNUALIZATION_FACTOR = 252
DEFAULT_RISK_FREE_RATE = 0.07
DEFAULT_VAR_CONFIDENCE = 0.95
DEFAULT_MIN_OBSERVATIONS = 60
DEFAULT_ROLLING_WINDOW = 30

RISK_THRESHOLDS = {
    "volatility": {"low": 0.10, "high": 0.30},
    "beta": {"low": 0.90, "high": 1.10},
    "concentration": {"low": 0.20, "high": 0.40},
    "var": {"low": 0.02, "high": 0.05},
    "drawdown": {"low": 0.10, "high": 0.25},
    "cvar": {"low": 0.03, "high": 0.08},
}


@dataclass
class RiskMetrics:
    portfolio_beta: Optional[float] = None
    annualized_volatility: Optional[float] = None
    portfolio_variance: Optional[float] = None
    var_95: Optional[float] = None
    expected_shortfall_95: Optional[float] = None
    max_drawdown: Optional[float] = None
    rolling_volatility_30d: Optional[float] = None
    hhi: Optional[float] = None
    top_holding_concentration: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    correlation_diversification_score: Optional[float] = None
    structural_diversification_score: Optional[float] = None
    overall_diversification_score: Optional[float] = None
    diversification_score: Optional[float] = None
    risk_score: Optional[float] = None
    risk_contributions: Dict[str, float] = field(default_factory=dict)
    stress_test: Dict[str, Any] = field(default_factory=dict)
    holdings_count: int = 0
    history_days: int = 0
    benchmark_symbol: str = DEFAULT_BENCHMARK
    covariance_matrix: Optional[pd.DataFrame] = None
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        covariance_payload = None
        if self.covariance_matrix is not None:
            covariance_payload = self.covariance_matrix.round(4).to_dict()
        return {
            "portfolio_beta": self.portfolio_beta,
            "annualized_volatility": self.annualized_volatility,
            "portfolio_variance": self.portfolio_variance,
            "var_95": self.var_95,
            "expected_shortfall_95": self.expected_shortfall_95,
            "max_drawdown": self.max_drawdown,
            "rolling_volatility_30d": self.rolling_volatility_30d,
            "hhi": self.hhi,
            "top_holding_concentration": self.top_holding_concentration,
            "sharpe_ratio": self.sharpe_ratio,
            "correlation_diversification_score": self.correlation_diversification_score,
            "structural_diversification_score": self.structural_diversification_score,
            "overall_diversification_score": self.overall_diversification_score,
            "diversification_score": self.diversification_score,
            "risk_score": self.risk_score,
            "risk_contributions": self.risk_contributions,
            "stress_test": self.stress_test,
            "holdings_count": self.holdings_count,
            "history_days": self.history_days,
            "benchmark_symbol": self.benchmark_symbol,
            "covariance_matrix": covariance_payload,
            "summary": self.summary,
        }


class RiskScoringEngine:
    """Separate scoring layer that summarizes risk metrics into a single score."""

    def __init__(self, thresholds: Optional[Dict[str, Any]] = None) -> None:
        self.thresholds = thresholds or RISK_THRESHOLDS

    def score_metrics(self, metrics: RiskMetrics) -> Optional[float]:
        if metrics.annualized_volatility is None or metrics.portfolio_beta is None:
            return None
        if metrics.hhi is None or metrics.var_95 is None:
            return None

        volatility_risk = self._score_component(metrics.annualized_volatility, self.thresholds["volatility"])
        beta_risk = self._score_component(metrics.portfolio_beta, self.thresholds["beta"], use_absolute=False)
        concentration_risk = self._score_component(metrics.hhi, self.thresholds["concentration"], use_absolute=False)
        var_risk = self._score_component(metrics.var_95, self.thresholds["var"], use_absolute=False)
        cvar_risk = self._score_component(metrics.expected_shortfall_95 or 0.0, self.thresholds["cvar"], use_absolute=False)
        drawdown_risk = self._score_component(metrics.max_drawdown or 0.0, self.thresholds["drawdown"], use_absolute=False)

        risk_score = (
            0.25 * volatility_risk
            + 0.15 * beta_risk
            + 0.20 * concentration_risk
            + 0.15 * var_risk
            + 0.10 * cvar_risk
            + 0.15 * drawdown_risk
        )
        return round(float(risk_score), 2)

    def score_individual_metrics(
        self,
        volatility: Optional[float],
        beta: Optional[float],
        var_95: Optional[float],
        expected_shortfall_95: Optional[float],
        drawdown: Optional[float],
    ) -> Optional[float]:
        """Score an individual holding using volatility, beta, VaR, CVaR and drawdown."""
        if volatility is None or beta is None or var_95 is None:
            return None

        volatility_risk = self._score_component(volatility, self.thresholds["volatility"])
        beta_risk = self._score_component(beta, self.thresholds["beta"], use_absolute=False)
        var_risk = self._score_component(var_95, self.thresholds["var"], use_absolute=False)
        cvar_risk = self._score_component(expected_shortfall_95 or 0.0, self.thresholds["cvar"], use_absolute=False)
        drawdown_risk = self._score_component(drawdown or 0.0, self.thresholds["drawdown"], use_absolute=False)

        risk_score = (
            0.30 * volatility_risk
            + 0.20 * beta_risk
            + 0.20 * var_risk
            + 0.15 * cvar_risk
            + 0.15 * drawdown_risk
        )
        return round(float(risk_score), 2)

    def classify_risk_level(self, score: Optional[float]) -> Optional[str]:
        """Classify a numeric risk score into a human-readable level."""
        if score is None:
            return None
        if score < 35:
            return "Low"
        if score < 55:
            return "Moderate"
        if score < 75:
            return "High"
        return "Very High"

    @staticmethod
    def _score_component(value: float, threshold: Dict[str, float], use_absolute: bool = True) -> float:
        low = threshold.get("low", 0.0)
        high = threshold.get("high", 1.0)
        if not np.isfinite(value):
            return 0.0
        if use_absolute:
            normalized = value
        else:
            normalized = abs(value)
        if normalized <= low:
            return 0.0
        if normalized >= high:
            return 100.0
        span = high - low
        if span <= 0:
            return 100.0
        return float(min(100.0, max(0.0, ((normalized - low) / span) * 100.0)))


class RiskEngine:
    """Industry-grade portfolio risk engine with dashboard-ready JSON output."""

    def __init__(
        self,
        yahoo_client: Optional[YahooFinanceClient] = None,
        benchmark_symbol: str = DEFAULT_BENCHMARK,
        history_period: str = DEFAULT_HISTORY_PERIOD,
        annualization_factor: int = DEFAULT_ANNUALIZATION_FACTOR,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.yahoo_client = yahoo_client or YahooFinanceClient()
        self.benchmark_symbol = benchmark_symbol
        self.history_period = history_period
        self.annualization_factor = annualization_factor
        self.scoring_engine = RiskScoringEngine(thresholds=thresholds)

    def evaluate_portfolio(
        self,
        portfolio: Union[Dict[str, Any], List[Dict[str, Any]]],
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    ) -> Dict[str, Any]:
        """Evaluate either a portfolio JSON object or a holdings list."""
        holdings = self._extract_holdings(portfolio)
        if not holdings:
            raise ValueError("Portfolio holdings list cannot be empty.")

        normalized_holdings = self._normalize_holdings(holdings)
        if normalized_holdings.empty:
            raise ValueError("No holdings could be normalized for risk evaluation.")

        total_portfolio_value = float(normalized_holdings["live_value"].sum())
        weights = self._calculate_weights(normalized_holdings)
        returns_df, price_observations = self._fetch_returns_for_holdings(normalized_holdings)

        if returns_df.empty:
            raise RuntimeError("Unable to fetch historical returns for any holdings.")

        aligned_returns = self._align_returns(returns_df)
        if aligned_returns.empty:
            raise RuntimeError("No common historical return window is available across holdings.")

        valid_weights = self._sync_weights_to_returns(weights, aligned_returns.columns)
        portfolio_returns = self._calculate_portfolio_returns(aligned_returns, valid_weights)
        benchmark_returns = self._fetch_symbol_returns(self.benchmark_symbol)

        covariance_matrix = self.calculate_covariance_matrix(aligned_returns)
        portfolio_variance = self.calculate_portfolio_variance(valid_weights, covariance_matrix)

        metrics = RiskMetrics(
            holdings_count=len(valid_weights),
            benchmark_symbol=self.benchmark_symbol,
            history_days=len(portfolio_returns),
            covariance_matrix=covariance_matrix,
        )

        metrics.annualized_volatility = self.calculate_annualized_volatility_from_variance(
            portfolio_variance, self.annualization_factor
        )
        metrics.portfolio_variance = portfolio_variance
        metrics.var_95 = self.calculate_historical_var(portfolio_returns)
        metrics.expected_shortfall_95 = self.calculate_expected_shortfall(portfolio_returns)
        metrics.max_drawdown = self.calculate_max_drawdown(portfolio_returns)
        metrics.rolling_volatility_30d = self.calculate_rolling_volatility(portfolio_returns)
        metrics.hhi = self.calculate_hhi(valid_weights)
        metrics.top_holding_concentration = float(valid_weights.max()) if not valid_weights.empty else None
        metrics.sharpe_ratio = self.calculate_sharpe_ratio(portfolio_returns, risk_free_rate)
        corr_score, structural_score, overall_score = self.calculate_diversification_scores(
            valid_weights, aligned_returns, metrics.hhi
        )
        metrics.correlation_diversification_score = corr_score
        metrics.structural_diversification_score = structural_score
        metrics.overall_diversification_score = overall_score
        metrics.diversification_score = overall_score
        metrics.portfolio_beta = self.calculate_portfolio_beta(portfolio_returns, benchmark_returns)
        metrics.risk_contributions = self.calculate_risk_contributions(valid_weights, covariance_matrix)
        metrics.stress_test = self.run_stress_test(
            valid_weights, normalized_holdings, benchmark_returns, aligned_returns
        )
        metrics.risk_score = self.calculate_risk_score(metrics)

        metrics.summary = {
            "annualized_volatility": metrics.annualized_volatility,
            "portfolio_variance": metrics.portfolio_variance,
            "var_95": metrics.var_95,
            "expected_shortfall_95": metrics.expected_shortfall_95,
            "max_drawdown": metrics.max_drawdown,
            "rolling_volatility_30d": metrics.rolling_volatility_30d,
            "hhi": metrics.hhi,
            "top_holding_concentration": metrics.top_holding_concentration,
            "sharpe_ratio": metrics.sharpe_ratio,
            "risk_score_type": "Composite risk score based on volatility, beta, concentration, VaR, CVaR, and drawdown.",
            "sharpe_ratio_type": "Annualized excess return per unit volatility.",
            "correlation_diversification_score": metrics.correlation_diversification_score,
            "structural_diversification_score": metrics.structural_diversification_score,
            "overall_diversification_score": metrics.overall_diversification_score,
            "diversification_score": metrics.diversification_score,
            "portfolio_beta": metrics.portfolio_beta,
            "risk_score": metrics.risk_score,
            "history_days": metrics.history_days,
            "holdings_count": metrics.holdings_count,
            "risk_contributions": metrics.risk_contributions,
            "stress_test": metrics.stress_test,
        }

        sector_metrics = self._calculate_sector_metrics(normalized_holdings)
        correlation_matrix = self.calculate_correlation_matrix(aligned_returns)
        correlation_section = self._correlation_details(correlation_matrix)
        risk_summary = self._build_risk_summary(metrics, total_portfolio_value)
        concentration_risk = self._build_concentration_section(valid_weights, sector_metrics)
        diversification_section = self._build_diversification_section(metrics, correlation_section)
        insights = self._build_insights(metrics, concentration_risk, sector_metrics, correlation_section)

        holding_engine = HoldingRiskEngine(
            normalized_holdings=normalized_holdings,
            returns_df=aligned_returns,
            benchmark_returns=benchmark_returns,
            portfolio_weights=valid_weights,
            covariance_matrix=covariance_matrix,
            risk_engine=self,
            risk_free_rate=risk_free_rate,
        )
        holding_analysis, holding_summary = holding_engine.build_analysis()

        portfolio_meta = portfolio if isinstance(portfolio, dict) else {}
        holding_analysis_df = pd.DataFrame(holding_analysis)
        merged_holdings = normalized_holdings.merge(holding_analysis_df,on="symbol",how="left",suffixes=("", "_analysis"))
        
        return {
            "client_code": portfolio_meta.get("client_code"),
            "client_name": portfolio_meta.get("client_name"),
            "portfolio_summary": portfolio_meta.get("summary", {}),
            "portfolio": {
                "benchmark": self.benchmark_symbol,
                "lookback_period": self.history_period,
                "risk_free_rate": risk_free_rate,
                "num_holdings": len(normalized_holdings),
                "total_portfolio_value": round(total_portfolio_value, 2),
            },
            "risk_summary": risk_summary,
            "concentration_risk": concentration_risk,
            "diversification": diversification_section,
            "correlation": correlation_section,
            "insights": insights,
            "risk_contributions": metrics.risk_contributions,
            "stress_test": metrics.stress_test,
            "data_quality": {
                "benchmark": self.benchmark_symbol,
                "history_days": len(portfolio_returns),
                "return_observations": len(aligned_returns),
                "holdings_requested": len(holdings),
                "holdings_processed": int(len(valid_weights)),
                "missing_history_symbols": [ticker for ticker, count in price_observations.items() if count == 0],
                "price_observations": price_observations,
            },
            "holdings": merged_holdings.to_dict(orient="records"),
            "correlation_matrix": correlation_matrix.round(4).to_dict(),
            "holding_analysis": holding_analysis,
            "holding_summary": holding_summary,
            "metrics": metrics.to_dict(),
        }

    def _extract_holdings(self, portfolio: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if isinstance(portfolio, list):
            holdings = portfolio
        elif isinstance(portfolio, dict):
            holdings = portfolio.get("holdings")
            if holdings is None:
                raise ValueError("Portfolio dict must include a 'holdings' list.")
            if not isinstance(holdings, list):
                raise TypeError("'holdings' must be a list of holding dictionaries.")
        else:
            raise TypeError("Portfolio must be a dict or a list of holdings.")

        if not holdings:
            raise ValueError("Portfolio contains no holdings.")

        return holdings

    def _normalize_holdings(self, holdings: List[Dict[str, Any]]) -> pd.DataFrame:
        """Normalize holdings into a DataFrame with symbol and live_value columns."""
        df = pd.DataFrame(holdings)
        if df.empty:
            return pd.DataFrame()

        df = df.copy()
        if "live_value" not in df.columns:
            df["live_value"] = df.get("quantity", 0) * df.get("live_price", 0)

        df["live_value"] = pd.to_numeric(df["live_value"], errors="coerce").fillna(0.0)
        df["symbol"] = df.apply(self._resolve_symbol, axis=1)
        df = df.dropna(subset=["symbol"]).reset_index(drop=True)
        df = df.loc[df["live_value"] > 0].reset_index(drop=True)

        if df.empty:
            logger.warning("Holdings normalization dropped all rows because of missing symbols or zero live value.")

        return df

    def _resolve_symbol(self, row: pd.Series) -> Optional[str]:
        """Resolve a symbol from the holding using its symbol or ISIN."""
        symbol = row.get("symbol")
        if symbol and isinstance(symbol, str) and symbol.strip():
            return symbol.strip()

        isin = row.get("isin")
        if not isin or not isinstance(isin, str):
            return None

        resolved = self.yahoo_client._get_symbol_from_isin(isin)
        if not resolved:
            logger.warning("Unable to resolve symbol for ISIN %s", isin)
        return resolved

    def _calculate_weights(self, holdings_df: pd.DataFrame) -> pd.Series:
        """Calculate portfolio weights from live values."""
        total_value = holdings_df["live_value"].sum()
        if total_value <= 0:
            raise ValueError("Total live portfolio value must be greater than zero.")
        return (holdings_df.set_index("symbol")["live_value"] / total_value).sort_values(ascending=False)

    def _fetch_returns_for_holdings(self, holdings_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
        """Fetch historical daily returns for each holding and return observation counts."""
        returns_by_symbol: Dict[str, pd.Series] = {}
        price_observations: Dict[str, int] = {}

        for _, row in holdings_df.iterrows():
            symbol = row["symbol"]
            returns = self._fetch_symbol_returns(symbol)
            price_observations[symbol] = int(len(returns))
            if returns.empty:
                logger.warning("No historical returns available for symbol %s", symbol)
                continue
            returns_by_symbol[symbol] = returns.rename(symbol)
        if not returns_by_symbol:
            return pd.DataFrame(), price_observations

        return pd.DataFrame(returns_by_symbol), price_observations

    def _fetch_symbol_returns(self, symbol: str) -> pd.Series:
        """Fetch daily returns for a Yahoo Finance symbol."""
        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=self.history_period, auto_adjust=True)
            if history.empty or "Close" not in history.columns:
                return pd.Series(dtype=float)
            series = history["Close"].pct_change(fill_method=None).dropna()
            series.index = pd.to_datetime(series.index)
            return series
        except Exception as exc:
            logger.exception("Failed to fetch historical returns for %s: %s", symbol, exc)
            return pd.Series(dtype=float)

    def _align_returns(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Align return series across holdings with an inner join on dates."""
        aligned = returns_df.dropna(how="any")
        if aligned.empty:
            logger.warning("Alignment of historical returns produced no common history.")
        return aligned

    def _sync_weights_to_returns(self, weights: pd.Series, symbols: Sequence[str]) -> pd.Series:
        """Sync weights to the assets for which historical returns are available."""
        valid = weights.loc[weights.index.intersection(symbols)].copy()
        if valid.empty:
            raise RuntimeError("No portfolio weights remain after synchronizing with available return history.")
        return (valid / valid.sum()).sort_values(ascending=False)

    def _calculate_portfolio_returns(self, returns_df: pd.DataFrame, weights: pd.Series) -> pd.Series:
        """Compute daily portfolio returns using vectorized weighted asset returns."""
        if returns_df.empty or weights.empty:
            return pd.Series(dtype=float)
        missing_weights = set(weights.index) - set(returns_df.columns)
        if missing_weights:
            weights = weights.drop(index=missing_weights)
        return returns_df[weights.index].mul(weights, axis=1).sum(axis=1)

    def calculate_covariance_matrix(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate the covariance matrix for the aligned return series."""
        if returns_df.empty or returns_df.shape[1] < 2:
            return pd.DataFrame(index=returns_df.columns, columns=returns_df.columns, dtype=float)
        return returns_df.cov()

    def calculate_portfolio_variance(self, weights: pd.Series, covariance_matrix: pd.DataFrame) -> Optional[float]:
        """Calculate portfolio variance using the covariance matrix: w^T Sigma w."""
        if weights.empty or covariance_matrix.empty:
            return None
        aligned_cov = covariance_matrix.loc[weights.index, weights.index]
        weight_vector = weights.loc[aligned_cov.index].to_numpy(dtype=float)
        return float(weight_vector @ aligned_cov.to_numpy(dtype=float) @ weight_vector)

    def calculate_annualized_volatility_from_variance(
        self, portfolio_variance: Optional[float], annualization_factor: Optional[int] = None
    ) -> Optional[float]:
        """Convert portfolio variance to annualized volatility."""
        if portfolio_variance is None or portfolio_variance < 0:
            return None
        factor = annualization_factor or self.annualization_factor
        return float(np.sqrt(portfolio_variance * factor))

    def calculate_annualized_volatility(self, portfolio_returns: pd.Series) -> Optional[float]:
        """Calculate annualized portfolio volatility from daily returns."""
        if portfolio_returns.empty:
            return None
        daily_std = float(portfolio_returns.std(ddof=1))
        return float(daily_std * np.sqrt(self.annualization_factor))

    def calculate_historical_var(self, portfolio_returns: pd.Series, confidence_level: float = DEFAULT_VAR_CONFIDENCE) -> Optional[float]:
        """Calculate historical Value at Risk (VaR) at the given confidence level."""
        if portfolio_returns.empty:
            return None
        percentile = 100 * (1 - confidence_level)
        var_pct = np.percentile(portfolio_returns.dropna(), percentile)
        return float(abs(var_pct))

    def calculate_expected_shortfall(self, portfolio_returns: pd.Series, confidence_level: float = DEFAULT_VAR_CONFIDENCE) -> Optional[float]:
        """Calculate Expected Shortfall (CVaR) for the worst tail of daily returns."""
        if portfolio_returns.empty:
            return None
        losses = portfolio_returns.dropna()
        if losses.empty:
            return None
        tail_threshold = np.percentile(losses, 100 * (1 - confidence_level))
        tail_losses = losses[losses <= tail_threshold]
        if tail_losses.empty:
            return None
        average_tail_loss = float(tail_losses.mean())
        return float(abs(average_tail_loss))

    def calculate_max_drawdown(self, portfolio_returns: pd.Series) -> Optional[float]:
        """Calculate the max drawdown from cumulative portfolio performance."""
        if portfolio_returns.empty:
            return None
        cum_returns = (1 + portfolio_returns).cumprod()
        running_max = cum_returns.cummax()
        drawdowns = cum_returns / running_max - 1.0
        return float(abs(drawdowns.min())) if not drawdowns.empty else None

    def calculate_rolling_volatility(self, portfolio_returns: pd.Series, window: int = DEFAULT_ROLLING_WINDOW) -> Optional[float]:
        """Calculate the latest rolling volatility for a short lookback window."""
        if portfolio_returns.empty:
            return None
        window = min(window, len(portfolio_returns))
        if window <= 1:
            return self.calculate_annualized_volatility(portfolio_returns)
        rolling_std = portfolio_returns.rolling(window=window).std(ddof=1)
        latest = rolling_std.dropna().iloc[-1] if rolling_std.dropna().any() else None
        if latest is None:
            return None
        return float(latest * np.sqrt(self.annualization_factor))

    def calculate_correlation_matrix(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate the correlation matrix for portfolio holdings."""
        if returns_df.shape[1] < 2:
            return pd.DataFrame()
        return returns_df.corr()

    def calculate_portfolio_beta(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> Optional[float]:
        """Calculate portfolio beta versus the benchmark returns."""
        if portfolio_returns.empty or benchmark_returns.empty:
            return None
        combined = pd.concat([portfolio_returns.rename("portfolio"), benchmark_returns.rename("benchmark")], axis=1).dropna()
        if len(combined) < DEFAULT_MIN_OBSERVATIONS:
            logger.warning(
                "Not enough paired observations to calculate portfolio beta. Got %s rows.",
                len(combined),
            )
            return None
        covariance = float(combined["portfolio"].cov(combined["benchmark"]))
        benchmark_variance = float(combined["benchmark"].var())
        if benchmark_variance <= 0:
            return None
        return float(covariance / benchmark_variance)

    def calculate_sharpe_ratio(
        self,
        portfolio_returns: pd.Series,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
    ) -> Optional[float]:
        """Calculate the annualized Sharpe ratio using a constant risk-free rate."""
        if portfolio_returns.empty:
            return None
        annual_return = (1 + portfolio_returns).prod() ** (self.annualization_factor / len(portfolio_returns)) - 1
        annual_volatility = self.calculate_annualized_volatility(portfolio_returns)
        if not annual_volatility or annual_volatility == 0:
            return None
        return float((annual_return - risk_free_rate) / annual_volatility)

    def calculate_hhi(self, weights: pd.Series) -> Optional[float]:
        """Calculate the Herfindahl-Hirschman Index for portfolio concentration."""
        if weights.empty:
            return None
        normalized = weights / weights.sum()
        return float((normalized.pow(2)).sum())

    def calculate_diversification_scores(
        self,
        weights: pd.Series,
        returns_df: pd.DataFrame,
        hhi: Optional[float] = None,
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if weights.empty or returns_df.empty:
            return None, None, None

        common_assets = weights.index.intersection(returns_df.columns)
        if len(common_assets) < 2:
            return 100.0, 100.0, 100.0

        w = weights.loc[common_assets].astype(float)
        w = w / w.sum()

        returns = returns_df[common_assets]
        vols = returns.std()
        cov_matrix = returns.cov()

        portfolio_volatility = float(np.sqrt((w.values @ cov_matrix.values) @ w.values))
        if portfolio_volatility <= 1e-10:
            return None, None, None

        weighted_average_volatility = float(np.dot(w.values, vols.values))
        diversification_ratio = weighted_average_volatility / portfolio_volatility

        correlation_score = round(
            max(0.0, min(100.0, ((diversification_ratio - 1.0) / diversification_ratio) * 100.0)),
            2,
        )

        structural_score = round(
            max(0.0, min(100.0, (1.0 - np.sum(w.values ** 2)) * 100.0)),
            2,
        )

        overall_score = round(
            max(0.0, min(100.0, 0.6 * structural_score + 0.4 * correlation_score)),
            2,
        )

        return float(correlation_score), float(structural_score), float(overall_score)

 

    def calculate_risk_contributions(self, weights: pd.Series, covariance_matrix: pd.DataFrame) -> Dict[str, float]:
        """Estimate each holding's contribution to portfolio variance."""
        if weights.empty or covariance_matrix.empty:
            return {}
        aligned_cov = covariance_matrix.loc[weights.index, weights.index]
        if aligned_cov.empty:
            return {}
        variance = self.calculate_portfolio_variance(weights, aligned_cov)
        if variance is None or variance <= 0:
            return {}
        contributions: Dict[str, float] = {}
        for ticker in weights.index:
            contribution = float(weights.loc[ticker] * (aligned_cov.loc[ticker].dot(weights.loc[aligned_cov.index])) / variance)
            contributions[ticker] = round(contribution, 4)
        return dict(sorted(contributions.items(), key=lambda item: item[1], reverse=True))

    def run_stress_test(
        self,
        weights: pd.Series,
        normalized_holdings: pd.DataFrame,
        benchmark_returns: pd.Series,
        returns_df: pd.DataFrame,
        scenarios: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Estimate portfolio impact for market and sector shock scenarios using betas and exposures."""
        if weights.empty:
            return {}
        sector_weights = self._calculate_sector_exposures(normalized_holdings)
        holding_betas = self._calculate_holding_betas(returns_df, benchmark_returns)
        scenario_map = scenarios or {
            "market_correction": {
                "market_shock_pct": -0.12,
                "sector_displacements": {"Banking": -0.03, "IT": -0.02, "Energy": -0.01},
            },
            "credit_shock": {
                "market_shock_pct": -0.15,
                "sector_displacements": {"Banking": -0.05, "Consumer Defensive": -0.01},
            },
            "tech_drawdown": {
                "market_shock_pct": -0.08,
                "sector_displacements": {"IT": -0.06, "Consumer Defensive": -0.01},
            },
        }
        results: Dict[str, Any] = {}
        for name, scenario in scenario_map.items():
            market_shock_pct = float(scenario.get("market_shock_pct", 0.0))
            sector_displacements = scenario.get("sector_displacements", {})
            portfolio_impact = 0.0
            exposure_details: Dict[str, float] = {}
            for symbol, weight in weights.items():
                symbol_weight = float(weight)
                holding_sector = self._find_holding_sector(normalized_holdings, symbol)
                sector_adjustment = float(sector_displacements.get(holding_sector, 0.0))
                fallback_beta = self.portfolio_beta if hasattr(self, "portfolio_beta") and self.portfolio_beta is not None else 1.0
                beta = float(holding_betas.get(symbol, fallback_beta))
                shock_pct = market_shock_pct + sector_adjustment
                holding_impact = beta * shock_pct * symbol_weight
                portfolio_impact += holding_impact
                if holding_sector:
                    exposure_details[holding_sector] = exposure_details.get(holding_sector, 0.0) + symbol_weight
            results[name] = {
                "portfolio_return_pct": round(portfolio_impact * 100.0, 2),
                "market_shock_pct": round(market_shock_pct * 100.0, 2),
                "sector_displacements": sector_displacements,
                "sector_exposure_pct": {sector: round(exposure * 100.0, 2) for sector, exposure in exposure_details.items()},
            }
        return results

    def _calculate_sector_exposures(self, normalized_holdings: pd.DataFrame) -> Dict[str, float]:
        exposures: Dict[str, float] = {}
        if normalized_holdings.empty or "sector" not in normalized_holdings.columns:
            return exposures
        total_value = normalized_holdings["live_value"].sum()
        if total_value <= 0:
            return exposures
        for _, row in normalized_holdings.iterrows():
            sector = str(row.get("sector") or "").strip()
            if not sector:
                continue
            exposures[sector] = exposures.get(sector, 0.0) + float(row.get("live_value", 0.0))
        return {sector: value / total_value for sector, value in exposures.items()}

    def _calculate_holding_betas(self, returns_df: pd.DataFrame, benchmark_returns: pd.Series) -> Dict[str, float]:
        betas: Dict[str, float] = {}
        if returns_df.empty or benchmark_returns.empty:
            return betas
        combined = pd.concat([returns_df, benchmark_returns.rename("benchmark")], axis=1).dropna()
        benchmark_variance = float(combined["benchmark"].var()) if not combined["benchmark"].empty else 0.0
        if benchmark_variance <= 0:
            return betas
        for symbol in returns_df.columns:
            if symbol not in combined.columns:
                continue
            covariance = float(combined[symbol].cov(combined["benchmark"]))
            betas[symbol] = float(covariance / benchmark_variance)
        return betas

    def _find_holding_sector(self, normalized_holdings: pd.DataFrame, symbol: str) -> str:
        row = normalized_holdings.loc[normalized_holdings["symbol"] == symbol]
        if row.empty:
            return ""
        sector = row.iloc[0].get("sector")
        return str(sector).strip() if sector is not None else ""

    def _calculate_correlation_score(self, returns_df: pd.DataFrame) -> Optional[float]:
        """Compute a correlation-based score that penalizes high average pairwise correlation."""
        corr = self.calculate_correlation_matrix(returns_df)
        if corr.empty:
            return None
        n = corr.shape[0]
        if n < 2:
            return 100.0
        off_diag = corr.where(~np.eye(n, dtype=bool))
        avg_corr = float(off_diag.stack().abs().mean())
        if np.isnan(avg_corr):
            return None
        score = 100.0 * (1.0 - avg_corr)
        return float(max(0.0, min(100.0, score)))

    def calculate_risk_score(self, metrics: RiskMetrics) -> Optional[float]:
        return self.scoring_engine.score_metrics(metrics)

    def _calculate_sector_metrics(self, holdings_df: pd.DataFrame) -> Dict[str, Any]:
        sectors = holdings_df.loc[holdings_df["sector"].notna() & (holdings_df["sector"] != ""), ["sector", "live_value"]].copy()
        if sectors.empty:
            return {
                "sector_count": 0,
                "top_sector": None,
                "top_sector_weight": None,
                "top_sector_weight_pct": None,
            }
        sector_weights = sectors.groupby("sector")["live_value"].sum()
        sector_weights = sector_weights / sector_weights.sum()
        top_sector = sector_weights.idxmax()
        top_weight = float(sector_weights.max())
        return {
            "sector_count": int(sector_weights.count()),
            "top_sector": top_sector,
            "top_sector_weight": round(top_weight, 4),
            "top_sector_weight_pct": round(top_weight * 100, 2),
        }

    def _correlation_details(self, correlation_matrix: pd.DataFrame) -> Dict[str, Any]:
        if correlation_matrix.empty:
            return {
                "average": None,
                "highest_pair": None,
                "ticker_count": 0,
            }
        avg_corr = self._average_pairwise_correlation(correlation_matrix)
        highest_pair = self._highest_correlation_pair(correlation_matrix)
        return {
            "average": float(round(avg_corr, 4)) if avg_corr is not None else None,
            "highest_pair": highest_pair,
            "ticker_count": int(correlation_matrix.shape[0]),
        }

    @staticmethod
    def _average_pairwise_correlation(correlation_matrix: pd.DataFrame) -> Optional[float]:
        if correlation_matrix.empty or correlation_matrix.shape[0] < 2:
            return None
        mask = ~np.eye(correlation_matrix.shape[0], dtype=bool)
        values = correlation_matrix.where(mask).stack().abs()
        if values.empty:
            return None
        return float(values.mean())

    @staticmethod
    def _highest_correlation_pair(correlation_matrix: pd.DataFrame) -> Optional[List[Any]]:
        if correlation_matrix.empty or correlation_matrix.shape[0] < 2:
            return None
        mask = ~np.eye(correlation_matrix.shape[0], dtype=bool)
        stacked = correlation_matrix.where(mask).stack()
        if stacked.empty:
            return None
        highest = stacked.abs().idxmax()
        value = float(stacked.loc[highest])
        return [highest[0], highest[1], round(value, 4)]

    def _build_risk_summary(self, metrics: RiskMetrics, total_portfolio_value: float) -> Dict[str, Any]:
        volatility_pct = round(metrics.annualized_volatility * 100, 2) if metrics.annualized_volatility is not None else None
        var_pct = round(metrics.var_95 * 100, 2) if metrics.var_95 is not None else None
        var_rupees = round(metrics.var_95 * total_portfolio_value, 2) if metrics.var_95 is not None else None
        cvar_pct = round(metrics.expected_shortfall_95 * 100, 2) if metrics.expected_shortfall_95 is not None else None
        drawdown_pct = round(metrics.max_drawdown * 100, 2) if metrics.max_drawdown is not None else None
        rolling_volatility_pct = round(metrics.rolling_volatility_30d * 100, 2) if metrics.rolling_volatility_30d is not None else None
        return {
            "risk_score": metrics.risk_score,
            "risk_level": self._classify_risk_level(metrics.risk_score),
            "portfolio_beta": metrics.portfolio_beta,
            "volatility": {
                "value_pct": volatility_pct,
                "level": self._classify_volatility_level(metrics.annualized_volatility),
            },
            "daily_var": {
                "percent": var_pct,
                "rupees": var_rupees,
                "confidence": DEFAULT_VAR_CONFIDENCE,
            },
            "expected_shortfall": {
                "percent": cvar_pct,
                "confidence": DEFAULT_VAR_CONFIDENCE,
            },
            "max_drawdown": {
                "percent": drawdown_pct,
            },
            "rolling_volatility_30d": {
                "value_pct": rolling_volatility_pct,
            },
            "sharpe_ratio": metrics.sharpe_ratio,
            "diversification_score": metrics.diversification_score,
        }

    @staticmethod
    def _classify_volatility_level(volatility: Optional[float]) -> Optional[str]:
        if volatility is None:
            return None
        if volatility < 0.12:
            return "Low"
        if volatility < 0.20:
            return "Moderate"
        if volatility < 0.30:
            return "Elevated"
        return "High"

    @staticmethod
    def _classify_risk_level(score: Optional[float]) -> Optional[str]:
        if score is None:
            return None
        if score < 35:
            return "Low"
        if score < 55:
            return "Moderate"
        if score < 75:
            return "High"
        return "Very High"

    def _build_concentration_section(self, weights: pd.Series, sector_metrics: Dict[str, Any]) -> Dict[str, Any]:
        hhi = self.calculate_hhi(weights)
        return {
            "top_holding_weight": round(float(weights.max()), 4) if not weights.empty else None,
            "top_holding_weight_pct": round(float(weights.max()) * 100, 2) if not weights.empty else None,
            "hhi": round(hhi, 6) if hhi is not None else None,
            "effective_holdings": round(float(1.0 / hhi), 2) if hhi and hhi > 0 else None,
            "concentration_level": self._classify_concentration_level(weights.max() if not weights.empty else None),
            "stock_count": int(len(weights)),
            "top_sector": sector_metrics.get("top_sector"),
            "top_sector_weight_pct": sector_metrics.get("top_sector_weight_pct"),
            "sector_count": sector_metrics.get("sector_count"),
        }

    @staticmethod
    def _classify_concentration_level(top_weight: Optional[float]) -> Optional[str]:
        if top_weight is None:
            return None
        if top_weight >= 0.45:
            return "Very High"
        if top_weight >= 0.30:
            return "High"
        if top_weight >= 0.20:
            return "Moderate"
        return "Low"

    def _build_diversification_section(self, metrics: RiskMetrics, correlation_section: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "score": metrics.overall_diversification_score,
            "correlation_score": metrics.correlation_diversification_score,
            "structural_score": metrics.structural_diversification_score,
            "overall_score": metrics.overall_diversification_score,
            "stock_count": metrics.holdings_count,
            "sector_count": correlation_section.get("ticker_count") if correlation_section.get("ticker_count") is not None else 0,
            "average_correlation": correlation_section.get("average"),
        }

    def _build_insights(
        self,
        metrics: RiskMetrics,
        concentration: Dict[str, Any],
        sector_metrics: Dict[str, Any],
        correlation_section: Dict[str, Any],
    ) -> List[str]:
        insights: List[str] = []
        if metrics.risk_score is not None:
            risk_level = self._classify_risk_level(metrics.risk_score)
            insights.append(f"Portfolio risk level is {risk_level.lower()}.")
        if concentration.get("top_holding_weight_pct") is not None:
            if concentration["top_holding_weight_pct"] >= 40:
                insights.append("Top holding concentration is elevated; consider trimming the largest position.")
            elif concentration["top_holding_weight_pct"] >= 30:
                insights.append("Top holding exposure is high; diversification may reduce downside risk.")
        if sector_metrics.get("top_sector_weight_pct") is not None and sector_metrics["top_sector_weight_pct"] >= 40:
            insights.append(
                f"The largest sector is {sector_metrics['top_sector']} at {sector_metrics['top_sector_weight_pct']}% of the portfolio."
            )
        if metrics.portfolio_beta is not None:
            beta = metrics.portfolio_beta
            if beta > 1.1:
                insights.append("Portfolio beta is above market, indicating higher sensitivity to market moves.")
            elif beta < 0.9:
                insights.append("Portfolio beta is below market, indicating lower sensitivity to broad market moves.")
            else:
                insights.append("Portfolio beta is close to market, indicating balanced market exposure.")
        if correlation_section.get("average") is not None:
            avg_corr = correlation_section["average"]
            if avg_corr > 0.6:
                insights.append("Holdings are strongly correlated, which limits diversification benefits.")
            elif avg_corr > 0.4:
                insights.append("Moderate correlation across holdings; diversification is helpful but not complete.")
            else:
                insights.append("Holdings exhibit low correlation, which supports diversification.")
        if metrics.var_95 is not None:
            pct = round(metrics.var_95 * 100, 2)
            insights.append(f"Estimated daily loss at 95% confidence is about {pct}%.")
        if metrics.expected_shortfall_95 is not None:
            pct = round(metrics.expected_shortfall_95 * 100, 2)
            insights.append(f"Expected shortfall in the worst tail is about {pct}%.")
        if metrics.max_drawdown is not None:
            pct = round(metrics.max_drawdown * 100, 2)
            insights.append(f"Maximum drawdown over the observed period is about {pct}%.")
        if metrics.risk_contributions:
            top_symbol = next(iter(metrics.risk_contributions))
            top_contribution = metrics.risk_contributions[top_symbol]
            insights.append(
                f"The largest contribution to portfolio risk currently comes from {top_symbol} at about {top_contribution * 100:.1f}%."
            )
        return insights


if __name__ == "__main__":
    engine = RiskEngine()
    portfolio_health_engine = PortfolioHealthEngine()
    example_portfolio = {
        "client_code": "4214763833",
        "client_name": "Abhishek",
        "summary": {
            "total_invested_value": 45000.0,
            "total_live_value": 27665.0,
            "total_unrealised_pnl": -17335.0,
        },
        "holdings": [
            {
                "stock_name": "Reliance Industries",
                "isin": "INE002A01018",
                "quantity": 10.0,
                "average_buy_price": 2450.0,
                "buy_value": 24500.0,
                "closing_price": 2550.0,
                "closing_value": 25550.0,
                "unrealised_pnl": 1000.0,
                "symbol": "RELIANCE.NS",
                "sector": "Energy",
                "industry": "Oil & Gas Refining & Marketing",
                "market_cap": 17815499177984,
                "pe_ratio": 22.048233,
                "dividend_yield": 0.46,
                "live_price": 1316.5,
                "live_value": 13165.0,
                "live_unrealised_pnl": -11335.0,
            },
            {
                "stock_name": "ITC Ltd",
                "isin": "INE154A01025",
                "quantity": 50.0,
                "average_buy_price": 410.0,
                "buy_value": 20500.0,
                "closing_price": 490.0,
                "closing_value": 24500.0,
                "unrealised_pnl": 4000.0,
                "symbol": "ITC.NS",
                "sector": "Consumer Defensive",
                "industry": "Tobacco",
                "market_cap": 3633545740288,
                "pe_ratio": 17.575758,
                "dividend_yield": 5.52,
                "live_price": 290.0,
                "live_value": 14500.0,
                "live_unrealised_pnl": -6000.0,
            },
        ],
    }

    try:
        report = engine.evaluate_portfolio(example_portfolio)
        portfolio_health = portfolio_health_engine.calculate_health(report)
        import json

        print(json.dumps(report, indent=2, default=str))
        print(json.dumps(portfolio_health, indent=2, default=str))
    except Exception as exc:
        print(f"Risk engine execution failed: {exc}")
