import logging
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from backend.analytics.risk_engine import RiskEngine

logger = logging.getLogger(__name__)


class HoldingRiskEngine:
    """Compute risk and performance analytics for each individual holding."""

    def __init__(
        self,
        normalized_holdings: pd.DataFrame,
        returns_df: pd.DataFrame,
        benchmark_returns: pd.Series,
        portfolio_weights: pd.Series,
        covariance_matrix: pd.DataFrame,
        risk_engine: Optional["RiskEngine"] = None,
        risk_free_rate: float = 0.07,
    ) -> None:
        self.normalized_holdings = normalized_holdings.copy()
        self.returns_df = returns_df.copy()
        self.benchmark_returns = benchmark_returns.copy() if isinstance(benchmark_returns, pd.Series) else pd.Series(dtype=float)
        self.portfolio_weights = portfolio_weights.copy()
        self.covariance_matrix = covariance_matrix.copy() if isinstance(covariance_matrix, pd.DataFrame) else pd.DataFrame()
        self.risk_engine = risk_engine
        self.risk_free_rate = risk_free_rate
        self.scoring_engine = self._resolve_scoring_engine()

    def build_analysis(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Build per-holding analysis and an AI-ready summary payload."""
        if self.normalized_holdings.empty or self.returns_df.empty:
            return [], self._empty_summary()

        available_symbols = [symbol for symbol in self.portfolio_weights.index if symbol in self.returns_df.columns]
        if not available_symbols:
            return [], self._empty_summary()

        holding_analysis: List[Dict[str, Any]] = []
        for symbol in available_symbols:
            holding_row = self.normalized_holdings.loc[self.normalized_holdings["symbol"] == symbol]
            if holding_row.empty:
                continue

            holding_returns = self.returns_df[symbol].dropna()
            if holding_returns.empty:
                continue

            row = holding_row.iloc[0]
            weight = float(self.portfolio_weights.loc[symbol]) if symbol in self.portfolio_weights.index else 0.0
            weight_pct = round(weight * 100.0, 2)

            beta = self._calculate_beta(holding_returns)
            volatility = self._calculate_annualized_volatility(holding_returns)
            var95 = self._calculate_historical_var(holding_returns)
            expected_shortfall = self._calculate_expected_shortfall(holding_returns)
            drawdown = self._calculate_max_drawdown(holding_returns)
            sharpe = self._calculate_sharpe_ratio(holding_returns)
            risk_contribution_pct = self._calculate_risk_contribution_pct(symbol)
            performance_contribution_pct = self._calculate_performance_contribution_pct(holding_returns, weight)
            diversification_score = self._calculate_diversification_score(symbol)
            risk_score = self._calculate_risk_score(volatility, beta, var95, expected_shortfall, drawdown)
            risk_level = self._classify_risk_level(risk_score)

            holding_analysis.append(
                {
                    "symbol": symbol,
                    "company": self._get_company_name(row),
                    "sector": row.get("sector"),
                    "industry": row.get("industry"),
                    "weight": round(weight, 6),
                    "weight_pct": weight_pct,
                    "beta": round(beta, 4) if beta is not None else None,
                    "volatility_pct": round(volatility * 100.0, 2) if volatility is not None else None,
                    "var95_pct": round(var95 * 100.0, 2) if var95 is not None else None,
                    "expected_shortfall_pct": round(expected_shortfall * 100.0, 2) if expected_shortfall is not None else None,
                    "max_drawdown_pct": round(drawdown * 100.0, 2) if drawdown is not None else None,
                    "sharpe": round(sharpe, 4) if sharpe is not None else None,
                    "risk_score": int(round(risk_score)) if risk_score is not None else None,
                    "risk_level": risk_level,
                    "risk_contribution_pct": round(risk_contribution_pct, 2) if risk_contribution_pct is not None else None,
                    "performance_contribution_pct": round(performance_contribution_pct, 2) if performance_contribution_pct is not None else None,
                    "diversification_score": round(diversification_score, 2) if diversification_score is not None else None,
                }
            )

        holding_analysis.sort(
            key=lambda item: (item["risk_score"] if item["risk_score"] is not None else -1, item["weight_pct"]),
            reverse=True,
        )
        summary = self._build_summary(holding_analysis)
        return holding_analysis, summary

    def _resolve_scoring_engine(self) -> Any:
        if self.risk_engine is not None and hasattr(self.risk_engine, "scoring_engine"):
            return self.risk_engine.scoring_engine

        from backend.analytics.risk_engine import RiskScoringEngine

        return RiskScoringEngine()

    def _calculate_beta(self, holding_returns: pd.Series) -> Optional[float]:
        if self.risk_engine is not None:
            return self.risk_engine.calculate_portfolio_beta(holding_returns, self.benchmark_returns)

        if holding_returns.empty or self.benchmark_returns.empty:
            return None
        combined = pd.concat([holding_returns.rename("holding"), self.benchmark_returns.rename("benchmark")], axis=1).dropna()
        if combined.empty:
            return None
        covariance = float(combined["holding"].cov(combined["benchmark"]))
        benchmark_variance = float(combined["benchmark"].var())
        if benchmark_variance <= 0:
            return None
        return float(covariance / benchmark_variance)

    def _calculate_annualized_volatility(self, holding_returns: pd.Series) -> Optional[float]:
        if self.risk_engine is not None:
            return self.risk_engine.calculate_annualized_volatility(holding_returns)
        if holding_returns.empty:
            return None
        daily_std = float(holding_returns.std(ddof=1))
        return float(daily_std * (252.0 ** 0.5))

    def _calculate_historical_var(self, holding_returns: pd.Series) -> Optional[float]:
        if self.risk_engine is not None:
            return self.risk_engine.calculate_historical_var(holding_returns)
        if holding_returns.empty:
            return None
        percentile = np.percentile(holding_returns.dropna(), 5)
        return float(abs(percentile))

    def _calculate_expected_shortfall(self, holding_returns: pd.Series) -> Optional[float]:
        if self.risk_engine is not None:
            return self.risk_engine.calculate_expected_shortfall(holding_returns)
        if holding_returns.empty:
            return None
        losses = holding_returns.dropna()
        tail_threshold = np.percentile(losses, 5)
        tail_losses = losses[losses <= tail_threshold]
        if tail_losses.empty:
            return None
        return float(abs(tail_losses.mean()))

    def _calculate_max_drawdown(self, holding_returns: pd.Series) -> Optional[float]:
        if self.risk_engine is not None:
            return self.risk_engine.calculate_max_drawdown(holding_returns)
        if holding_returns.empty:
            return None
        cum_returns = (1 + holding_returns).cumprod()
        running_max = cum_returns.cummax()
        drawdowns = cum_returns / running_max - 1.0
        return float(abs(drawdowns.min())) if not drawdowns.empty else None

    def _calculate_sharpe_ratio(self, holding_returns: pd.Series) -> Optional[float]:
        if self.risk_engine is not None:
            return self.risk_engine.calculate_sharpe_ratio(holding_returns, self.risk_free_rate)
        if holding_returns.empty:
            return None
        annual_return = (1 + holding_returns).prod() ** (252.0 / len(holding_returns)) - 1
        annual_volatility = self._calculate_annualized_volatility(holding_returns)
        if annual_volatility is None or annual_volatility == 0:
            return None
        return float((annual_return - self.risk_free_rate) / annual_volatility)

    def _calculate_risk_contribution_pct(self, symbol: str) -> Optional[float]:
        if self.risk_engine is not None and not self.covariance_matrix.empty:
            contributions = self.risk_engine.calculate_risk_contributions(self.portfolio_weights, self.covariance_matrix)
            if symbol in contributions:
                return float(contributions[symbol]) * 100.0
        return None

    def _calculate_performance_contribution_pct(self, holding_returns: pd.Series, weight: float) -> Optional[float]:
        if holding_returns.empty:
            return None
        average_daily_return = float(holding_returns.mean())
        return average_daily_return * weight * 100.0

    def _calculate_diversification_score(self, symbol: str) -> Optional[float]:
        if self.returns_df.empty or symbol not in self.returns_df.columns:
            return None
        correlation_matrix = self.returns_df.corr()
        if correlation_matrix.empty or correlation_matrix.shape[0] < 2:
            return 100.0
        correlations = correlation_matrix[symbol].drop(index=symbol)
        if correlations.empty:
            return 100.0
        average_correlation = float(correlations.abs().mean())
        weight = self.portfolio_weights.loc[symbol] if symbol in self.portfolio_weights.index else 0.0
        return float(max(0.0, min(100.0, (1.0 - average_correlation) * 100.0 * weight)))

    def _calculate_risk_score(
        self,
        volatility: Optional[float],
        beta: Optional[float],
        var95: Optional[float],
        expected_shortfall: Optional[float],
        drawdown: Optional[float],
    ) -> Optional[float]:
        if self.scoring_engine is None:
            return None
        return self.scoring_engine.score_individual_metrics(volatility, beta, var95, expected_shortfall, drawdown)

    def _classify_risk_level(self, score: Optional[float]) -> Optional[str]:
        if self.scoring_engine is None:
            return None
        return self.scoring_engine.classify_risk_level(score)

    def _get_company_name(self, row: pd.Series) -> str:
        company = row.get("company_name") or row.get("stock_name") or row.get("company") or row.get("name")
        if company is None:
            return ""
        return str(company)

    def _empty_summary(self) -> Dict[str, Any]:
        return {
            "highest_risk_stock": None,
            "lowest_risk_stock": None,
            "largest_risk_contributor": None,
            "largest_return_contributor": None,
            "worst_performing_stock": None,
            "best_performing_stock": None,
            "best_diversifier": None,
            "worst_diversifier": None,
        }

    def _build_summary(self, holding_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not holding_analysis:
            return self._empty_summary()

        highest_risk_stock = max(holding_analysis, key=lambda item: item["risk_score"] or 0)
        lowest_risk_stock = min(holding_analysis, key=lambda item: item["risk_score"] if item["risk_score"] is not None else float("inf"))
        largest_risk_contributor = max(
            holding_analysis,
            key=lambda item: item["risk_contribution_pct"] if item["risk_contribution_pct"] is not None else float("-inf"),
        )
        largest_return_contributor = max(
            holding_analysis,
            key=lambda item: item["performance_contribution_pct"] if item["performance_contribution_pct"] is not None else float("-inf"),
        )
        worst_performing_stock = min(
            holding_analysis,
            key=lambda item: item["performance_contribution_pct"] if item["performance_contribution_pct"] is not None else float("inf"),
        )
        best_performing_stock = max(
            holding_analysis,
            key=lambda item: item["performance_contribution_pct"] if item["performance_contribution_pct"] is not None else float("-inf"),
        )
        best_diversifier = max(
            holding_analysis,
            key=lambda item: item["diversification_score"] if item["diversification_score"] is not None else float("-inf"),
        )
        worst_diversifier = min(
            holding_analysis,
            key=lambda item: item["diversification_score"] if item["diversification_score"] is not None else float("inf"),
        )

        return {
            "highest_risk_stock": highest_risk_stock.get("symbol"),
            "lowest_risk_stock": lowest_risk_stock.get("symbol"),
            "largest_risk_contributor": largest_risk_contributor.get("symbol"),
            "largest_return_contributor": largest_return_contributor.get("symbol"),
            "worst_performing_stock": worst_performing_stock.get("symbol"),
            "best_performing_stock": best_performing_stock.get("symbol"),
            "best_diversifier": best_diversifier.get("symbol"),
            "worst_diversifier": worst_diversifier.get("symbol"),
        }
