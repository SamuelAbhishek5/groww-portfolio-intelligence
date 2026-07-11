import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PortfolioHealthEngine:
    """Evaluate overall portfolio quality from risk-engine JSON output."""

    WEIGHTS = {
        "risk": 0.30,
        "diversification": 0.20,
        "performance": 0.20,
        "concentration": 0.10,
        "quality": 0.10,
        "stability": 0.10,
    }
    PERFORMANCE_THRESHOLDS = {
        "excellent": 25.0,
        "good": 10.0,
        "neutral": 0.0,
        "weak": -10.0,
        "poor": -20.0,
    }
    CONCENTRATION_THRESHOLDS = {
        "low": 20.0,
        "moderate": 30.0,
        "elevated": 40.0,
        "high": 50.0,
    }
    STABILITY_THRESHOLDS = {
        "high_sharpe": 1.0,
        "moderate_sharpe": 0.5,
        "neutral_sharpe": 0.0,
        "drawdown_penalty_max": 20.0,
        "volatility_low": 15.0,
        "volatility_moderate": 20.0,
        "volatility_high": 30.0,
    }
    QUALITY_THRESHOLDS = {
        "market_cap": 1_000_000_000_000,
        "pe_min": 5.0,
        "pe_max": 30.0,
        "dividend_yield": 1.0,
        "beta_min": 0.8,
        "beta_max": 1.2,
        "sharpe_positive": 0.0,
    }
    DIVERSIFICATION_THRESHOLDS = {
        "holdings": [(10, 100.0), (7, 85.0), (5, 70.0), (3, 50.0), (2, 25.0), (1, 0.0)],
        "sectors": [(6, 100.0), (4, 80.0), (3, 60.0), (2, 40.0), (1, 0.0)],
        "correlation": [(0.2, 100.0), (0.4, 80.0), (0.6, 60.0), (0.8, 40.0), (1.0, 20.0)],
    }

    def calculate_health(self, portfolio_json: dict, benchmark_metrics: Optional[dict] = None) -> dict:
        """Return a portfolio-health assessment based on risk-engine output."""
        benchmark_metrics = benchmark_metrics or {}
        risk_health = self._calculate_risk_health(portfolio_json)
        performance_return_pct = self._calculate_return_pct(portfolio_json)
        benchmark_relative_performance_pct = self._coerce_float(
            benchmark_metrics.get("portfolio_relative_performance_pct")
        )
        performance_score = self._calculate_performance_score(
            performance_return_pct,
            benchmark_relative_performance_pct,
        )
        diversification = self._calculate_diversification(portfolio_json)
        concentration = self._calculate_concentration(portfolio_json)
        quality = self._calculate_quality(portfolio_json)
        stability = self._calculate_stability(portfolio_json)

        breakdown = {
            "risk": round(risk_health, 2),
            "diversification": round(diversification, 2),
            "performance": round(performance_score, 2),
            "concentration": round(concentration, 2),
            "quality": round(quality, 2),
            "stability": round(stability, 2),
        }

        weighted_scores = {
            "risk": round(self.WEIGHTS["risk"] * risk_health, 2),
            "diversification": round(self.WEIGHTS["diversification"] * diversification, 2),
            "performance": round(self.WEIGHTS["performance"] * performance_score, 2),
            "concentration": round(self.WEIGHTS["concentration"] * concentration, 2),
            "quality": round(self.WEIGHTS["quality"] * quality, 2),
            "stability": round(self.WEIGHTS["stability"] * stability, 2),
        }

        overall_score = self._clamp(sum(weighted_scores.values()), 0.0, 100.0)
        overall_score = round(overall_score, 2)

        grade, status = self._grade_and_status(overall_score)
        context = {
            "risk_health": risk_health,
            "diversification_score": diversification,
            "performance_score": performance_score,
            "performance_return_pct": performance_return_pct,
            "benchmark_relative_performance_pct": benchmark_relative_performance_pct,
            "concentration_score": concentration,
            "quality_score": quality,
            "stability_score": stability,
            "holdings_count": self._get_holdings_count(portfolio_json),
            "sector_count": self._get_sector_count(portfolio_json),
            "portfolio_beta": self._get_nested(portfolio_json, ["risk_summary", "portfolio_beta"], None),
            "volatility_pct": self._get_nested(portfolio_json, ["risk_summary", "volatility", "value_pct"], None),
            "sharpe_ratio": self._get_nested(portfolio_json, ["risk_summary", "sharpe_ratio"], None),
            "max_drawdown_pct": self._get_nested(portfolio_json, ["risk_summary", "max_drawdown", "percent"], None),
            "effective_holdings": self._get_nested(portfolio_json, ["concentration_risk", "effective_holdings"], None),
        }
        strengths = self._detect_strengths(portfolio_json, breakdown, context)
        weaknesses = self._detect_weaknesses(portfolio_json, breakdown, context)
        recommendations = self._generate_recommendations(portfolio_json, breakdown, context)
        summary = self._build_summary(portfolio_json, breakdown, context)

        return {
            "portfolio_health": {
                "overall_score": overall_score,
                "grade": grade,
                "status": status,
                "breakdown": breakdown,
                "weighted_scores": weighted_scores,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "recommendations": recommendations,
                "summary": summary,
            }
        }

    def _calculate_risk_health(self, portfolio_json: dict) -> float:
        risk_score = self._get_nested(portfolio_json, ["risk_summary", "risk_score"], 0.0)
        score = 100.0 - float(risk_score)
        return self._clamp(score, 0.0, 100.0)

    def _calculate_return_pct(self, portfolio_json: dict) -> float:
        invested_value = self._get_nested(portfolio_json, ["portfolio_summary", "total_invested_value"], 0.0)
        live_value = self._get_nested(portfolio_json, ["portfolio_summary", "total_live_value"], 0.0)
        if invested_value in (None, 0):
            return 0.0
        return ((float(live_value) - float(invested_value)) / float(invested_value)) * 100.0

    def _calculate_performance_score(
        self,
        return_pct: float,
        relative_performance_pct: Optional[float] = None,
    ) -> float:
        if return_pct >= self.PERFORMANCE_THRESHOLDS["excellent"]:
            score = 100.0
        elif return_pct >= self.PERFORMANCE_THRESHOLDS["good"]:
            score = 85.0
        elif return_pct >= self.PERFORMANCE_THRESHOLDS["neutral"]:
            score = 70.0
        elif return_pct >= self.PERFORMANCE_THRESHOLDS["weak"]:
            score = 55.0
        elif return_pct >= self.PERFORMANCE_THRESHOLDS["poor"]:
            score = 35.0
        else:
            score = 10.0

        if relative_performance_pct is not None:
            if relative_performance_pct < -10.0:
                score -= 25.0
            elif relative_performance_pct < -5.0:
                score -= 15.0
            elif relative_performance_pct < 0.0:
                score -= 10.0
            elif relative_performance_pct > 5.0:
                score += 5.0
        return self._clamp(score, 0.0, 100.0)

    def _calculate_diversification(self, portfolio_json: dict) -> float:
        holdings_count = self._get_holdings_count(portfolio_json)
        sector_count = self._get_sector_count(portfolio_json)
        average_correlation = self._get_nested(portfolio_json, ["correlation", "average"], None)
        effective_holdings = self._get_nested(portfolio_json, ["concentration_risk", "effective_holdings"], None)

        holdings_score = self._score_by_band(holdings_count, self.DIVERSIFICATION_THRESHOLDS["holdings"])
        sector_score = self._score_by_band(sector_count, self.DIVERSIFICATION_THRESHOLDS["sectors"])
        correlation_score = self._score_correlation(average_correlation)
        effective_score = self._score_effective_holdings(effective_holdings, holdings_count)

        score = (
            0.40 * holdings_score
            + 0.30 * sector_score
            + 0.20 * correlation_score
            + 0.10 * effective_score
        )
        if holdings_count <= 2 and score > 60.0:
            score = 60.0
        return self._clamp(score, 0.0, 100.0)

    def _calculate_concentration(self, portfolio_json: dict) -> float:
        top_weight_pct = self._get_nested(portfolio_json, ["concentration_risk", "top_holding_weight_pct"], None)
        hhi = self._get_nested(portfolio_json, ["concentration_risk", "hhi"], None)
        effective_holdings = self._get_nested(portfolio_json, ["concentration_risk", "effective_holdings"], None)

        if top_weight_pct is None:
            score = 100.0
        elif float(top_weight_pct) < self.CONCENTRATION_THRESHOLDS["low"]:
            score = 100.0
        elif float(top_weight_pct) < self.CONCENTRATION_THRESHOLDS["moderate"]:
            score = 80.0
        elif float(top_weight_pct) < self.CONCENTRATION_THRESHOLDS["elevated"]:
            score = 60.0
        elif float(top_weight_pct) < self.CONCENTRATION_THRESHOLDS["high"]:
            score = 40.0
        else:
            score = 20.0

        if hhi is not None:
            if float(hhi) > 0.5:
                score -= 35.0
            elif float(hhi) > 0.3:
                score -= 20.0
            elif float(hhi) > 0.2:
                score -= 10.0

        if effective_holdings is not None:
            if float(effective_holdings) <= 2:
                score -= 30.0
            elif float(effective_holdings) <= 3:
                score -= 20.0
            elif float(effective_holdings) <= 4:
                score -= 10.0

        return self._clamp(score, 0.0, 100.0)

    def _calculate_quality(self, portfolio_json: dict) -> float:
        holdings = portfolio_json.get("holdings", []) or []
        if not holdings:
            return 0.0

        holding_analysis = portfolio_json.get("holding_analysis", []) or []
        analysis_by_symbol = {item.get("symbol"): item for item in holding_analysis if item.get("symbol")}

        component_scores: List[float] = []
        for holding in holdings:
            score = 0.0
            market_cap = self._coerce_float(holding.get("market_cap"))
            if market_cap is None:
                market_cap = self._coerce_float(analysis_by_symbol.get(holding.get("symbol"), {}).get("market_cap"))
            if market_cap is not None and market_cap >= self.QUALITY_THRESHOLDS["market_cap"]:
                score += 30.0

            pe_ratio = self._coerce_float(holding.get("pe_ratio"))
            if pe_ratio is None:
                pe_ratio = self._coerce_float(analysis_by_symbol.get(holding.get("symbol"), {}).get("pe_ratio"))
            if pe_ratio is not None and self.QUALITY_THRESHOLDS["pe_min"] <= pe_ratio <= self.QUALITY_THRESHOLDS["pe_max"]:
                score += 20.0

            dividend_yield = self._coerce_float(holding.get("dividend_yield"))
            if dividend_yield is None:
                dividend_yield = self._coerce_float(analysis_by_symbol.get(holding.get("symbol"), {}).get("dividend_yield"))
            if dividend_yield is not None and dividend_yield > self.QUALITY_THRESHOLDS["dividend_yield"]:
                score += 20.0

            beta = self._coerce_float(holding.get("beta"))
            if beta is None:
                beta = self._coerce_float(analysis_by_symbol.get(holding.get("symbol"), {}).get("beta"))
            if beta is not None and self.QUALITY_THRESHOLDS["beta_min"] <= beta <= self.QUALITY_THRESHOLDS["beta_max"]:
                score += 15.0

            sharpe = self._coerce_float(holding.get("sharpe"))
            if sharpe is None:
                sharpe = self._coerce_float(analysis_by_symbol.get(holding.get("symbol"), {}).get("sharpe"))
            if sharpe is not None and sharpe > self.QUALITY_THRESHOLDS["sharpe_positive"]:
                score += 15.0

            component_scores.append(score)

        if not component_scores:
            return 0.0
        average_score = sum(component_scores) / len(component_scores)
        return self._clamp(average_score, 0.0, 100.0)

    def _calculate_stability(self, portfolio_json: dict) -> float:
        sharpe_ratio = self._get_nested(portfolio_json, ["risk_summary", "sharpe_ratio"], None)
        drawdown_pct = self._get_nested(portfolio_json, ["risk_summary", "max_drawdown", "percent"], None)
        volatility_pct = self._get_nested(portfolio_json, ["risk_summary", "volatility", "value_pct"], None)

        if sharpe_ratio is None:
            sharpe_score = 60.0
        elif float(sharpe_ratio) > self.STABILITY_THRESHOLDS["high_sharpe"]:
            sharpe_score = 100.0
        elif float(sharpe_ratio) >= self.STABILITY_THRESHOLDS["moderate_sharpe"]:
            sharpe_score = 80.0
        elif float(sharpe_ratio) >= self.STABILITY_THRESHOLDS["neutral_sharpe"]:
            sharpe_score = 60.0
        else:
            sharpe_score = 30.0

        drawdown_penalty = min(self.STABILITY_THRESHOLDS["drawdown_penalty_max"], float(drawdown_pct or 0.0) / 5.0)

        if volatility_pct is None:
            volatility_adjustment = 0.0
        elif float(volatility_pct) < self.STABILITY_THRESHOLDS["volatility_low"]:
            volatility_adjustment = 10.0
        elif float(volatility_pct) < self.STABILITY_THRESHOLDS["volatility_moderate"]:
            volatility_adjustment = 5.0
        elif float(volatility_pct) < self.STABILITY_THRESHOLDS["volatility_high"]:
            volatility_adjustment = 0.0
        else:
            volatility_adjustment = -10.0

        score = sharpe_score - drawdown_penalty + volatility_adjustment
        return self._clamp(score, 0.0, 100.0)

    def _grade_and_status(self, score: float) -> Tuple[str, str]:
        if score >= 90:
            return "A+", "Excellent"
        if score >= 80:
            return "A", "Very Healthy"
        if score >= 70:
            return "B", "Fair"
        if score >= 60:
            return "C", "Average"
        if score >= 50:
            return "D", "Needs Improvement"
        return "F", "Poor"

    def _detect_strengths(self, portfolio_json: dict, breakdown: Dict[str, float], context: Dict[str, Any]) -> List[str]:
        strengths: List[str] = []
        if context.get("holdings_count", 0) >= 8:
            strengths.append("Broad portfolio diversification")
        if context.get("sector_count", 0) >= 5:
            strengths.append("Exposure across multiple sectors")
        if context.get("portfolio_beta") is not None and float(context["portfolio_beta"]) < 1.0:
            strengths.append("Below-market beta")
        if context.get("volatility_pct") is not None and float(context["volatility_pct"]) < self.STABILITY_THRESHOLDS["volatility_low"]:
            strengths.append("Low volatility")
        if context.get("performance_return_pct", 0.0) > self.PERFORMANCE_THRESHOLDS["good"]:
            strengths.append("Positive returns")
        if context.get("quality_score", 0.0) > 80.0:
            strengths.append("High-quality holdings")
        if not strengths:
            strengths.append("Portfolio remains manageable with a clear improvement plan")
        return strengths

    def _detect_weaknesses(self, portfolio_json: dict, breakdown: Dict[str, float], context: Dict[str, Any]) -> List[str]:
        weaknesses: List[str] = []
        if self._get_nested(portfolio_json, ["risk_summary", "risk_score"], 0.0) is not None and float(self._get_nested(portfolio_json, ["risk_summary", "risk_score"], 0.0)) > 60.0:
            weaknesses.append("Portfolio risk score is elevated")
        if self._get_nested(portfolio_json, ["concentration_risk", "top_holding_weight_pct"], 0.0) is not None and float(self._get_nested(portfolio_json, ["concentration_risk", "top_holding_weight_pct"], 0.0)) > self.CONCENTRATION_THRESHOLDS["elevated"]:
            weaknesses.append("Top holding concentration is high")
        sharpe_ratio = context.get("sharpe_ratio")
        if sharpe_ratio is not None and float(sharpe_ratio) < 0.0:
            weaknesses.append("Negative risk-adjusted returns")
        if context.get("benchmark_relative_performance_pct") is not None and float(context["benchmark_relative_performance_pct"]) < 0.0:
            weaknesses.append("Portfolio underperformed the benchmark")
        if context.get("performance_return_pct", 0.0) < 0.0:
            weaknesses.append("Portfolio return is below zero")
        if self._get_nested(portfolio_json, ["risk_summary", "max_drawdown", "percent"], 0.0) is not None and float(self._get_nested(portfolio_json, ["risk_summary", "max_drawdown", "percent"], 0.0)) > 30.0:
            weaknesses.append("Max drawdown is elevated")
        if context.get("holdings_count", 0) <= 2:
            weaknesses.append("Portfolio is concentrated in very few holdings")
        if not weaknesses:
            weaknesses.append("Portfolio quality is generally stable but could be refined")
        return weaknesses

    def _generate_recommendations(self, portfolio_json: dict, breakdown: Dict[str, float], context: Dict[str, Any]) -> List[str]:
        recommendations: List[str] = []
        top_weight_pct = self._get_nested(portfolio_json, ["concentration_risk", "top_holding_weight_pct"], 0.0)
        if top_weight_pct is not None and float(top_weight_pct) > self.CONCENTRATION_THRESHOLDS["moderate"]:
            recommendations.append("Reduce exposure to the largest holding and diversify into additional names.")
        if context.get("performance_return_pct", 0.0) < 0.0:
            recommendations.append("Review underperforming positions and reallocate toward stronger long-term investments.")
        if context.get("benchmark_relative_performance_pct") is not None and float(context["benchmark_relative_performance_pct"]) < 0.0:
            recommendations.append("Review benchmark relative performance and adjust holdings to reduce underperformance.")
        if breakdown.get("diversification", 0.0) < 70.0:
            recommendations.append("Add holdings from different sectors to improve diversification.")
        sharpe_ratio = context.get("sharpe_ratio")
        if sharpe_ratio is not None and float(sharpe_ratio) < 0.0:
            recommendations.append("Replace holdings with poor risk-adjusted returns by stronger long-term investments.")
        if self._get_nested(portfolio_json, ["risk_summary", "max_drawdown", "percent"], 0.0) is not None and float(self._get_nested(portfolio_json, ["risk_summary", "max_drawdown", "percent"], 0.0)) > 20.0:
            recommendations.append("Increase defensive allocation or trim cyclical exposure to reduce drawdown risk.")
        if not recommendations:
            recommendations.append("Maintain the current allocation and monitor portfolio quality regularly.")
        return recommendations

    def _build_summary(self, portfolio_json: dict, breakdown: Dict[str, float], context: Dict[str, Any]) -> str:
        reasons: List[str] = []
        if context.get("performance_return_pct", 0.0) < 0.0:
            reasons.append("significant unrealized losses")
        if self._get_nested(portfolio_json, ["concentration_risk", "top_holding_weight_pct"], 0.0) is not None and float(self._get_nested(portfolio_json, ["concentration_risk", "top_holding_weight_pct"], 0.0)) > self.CONCENTRATION_THRESHOLDS["elevated"]:
            reasons.append("high concentration in a few holdings")
        if context.get("sharpe_ratio") is not None and float(context["sharpe_ratio"]) < 0.0:
            reasons.append("negative risk-adjusted returns")
        if context.get("quality_score", 0.0) > 80.0:
            reasons.append("fundamentally strong holdings")
        if context.get("portfolio_beta") is not None and float(context["portfolio_beta"]) < 1.0:
            reasons.append("below-market beta")

        if not reasons:
            return "The portfolio health is balanced, with no major concerns across risk, diversification, and stability."

        if breakdown.get("overall_score", 0.0) is None:
            del breakdown["overall_score"]
        reasons_text = ", ".join(reasons[:-1]) + f" and {reasons[-1]}" if len(reasons) > 1 else reasons[0]
        return f"The portfolio health is {self._describe_health_status(context.get('performance_return_pct', 0.0), context.get('quality_score', 0.0))} mainly because of {reasons_text}."

    def _describe_health_status(self, return_pct: float, quality_score: float) -> str:
        if return_pct < 0.0 and quality_score < 70.0:
            return "poor"
        if return_pct < 0.0:
            return "mixed"
        if quality_score > 80.0:
            return "healthy"
        return "stable"

    def _get_holdings_count(self, portfolio_json: dict) -> int:
        holdings = portfolio_json.get("holdings", []) or []
        return len(holdings)

    def _get_sector_count(self, portfolio_json: dict) -> int:
        holdings = portfolio_json.get("holdings", []) or []
        sectors = {str(holding.get("sector") or "").strip() for holding in holdings if str(holding.get("sector") or "").strip()}
        return len(sectors)

    def _score_by_band(self, value: int, bands: List[Tuple[int, float]]) -> float:
        for threshold, score in bands:
            if value >= threshold:
                return score
        return 0.0

    def _score_correlation(self, average_correlation: Optional[float]) -> float:
        if average_correlation is None:
            return 80.0
        if float(average_correlation) < 0.20:
            return 100.0
        if float(average_correlation) < 0.40:
            return 80.0
        if float(average_correlation) < 0.60:
            return 60.0
        if float(average_correlation) < 0.80:
            return 40.0
        return 20.0

    def _score_effective_holdings(self, effective_holdings: Optional[float], holdings_count: int) -> float:
        if effective_holdings is None:
            if holdings_count >= 6:
                return 100.0
            if holdings_count >= 4:
                return 80.0
            if holdings_count >= 3:
                return 60.0
            if holdings_count >= 2:
                return 40.0
            return 20.0
        if float(effective_holdings) >= 6.0:
            return 100.0
        if float(effective_holdings) >= 4.0:
            return 80.0
        if float(effective_holdings) >= 3.0:
            return 60.0
        if float(effective_holdings) >= 2.0:
            return 40.0
        return 20.0

    def _get_nested(self, data: Dict[str, Any], path: List[str], default: Any = None) -> Any:
        current: Any = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def _coerce_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, float(value)))
