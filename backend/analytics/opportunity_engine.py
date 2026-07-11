import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class OpportunityEngine:
    """Generate deterministic, rule-based portfolio findings from analytics outputs."""

    RULE_THRESHOLDS = {
        "sector_exposure_high": 40.0,
        "minimum_holdings": 5,
        "minimum_holdings_target": 8,
        "benchmark_underperformance_high": -10.0,
        "benchmark_underperformance_medium": -5.0,
        "risk_score_high": 70.0,
        "beta_high": 1.2,
        "beta_low": 1.0,
        "var_high": 3.0,
        "drawdown_high": 25.0,
        "risk_contribution_high": 0.50,
        "stress_test_threshold": -10.0,
        "diversification_high": 80.0,
        "diversification_low": 60.0,
        "dividend_high": 4.0,
        "valuation_high": 40.0,
        "valuation_low": 10.0,
    }
    VALUATION_THRESHOLDS = {
        "default": {
            "deep_value": 10.0,
            "value": 15.0,
            "fair": 25.0,
            "growth": 40.0,
        },
        "IT": {
            "deep_value": 15.0,
            "value": 25.0,
            "fair": 40.0,
            "growth": 60.0,
        },
        "Healthcare": {
            "deep_value": 15.0,
            "value": 25.0,
            "fair": 40.0,
            "growth": 60.0,
        },
        "Banking": {
            "deep_value": 8.0,
            "value": 12.0,
            "fair": 18.0,
            "growth": 25.0,
        },
    }
    IMPORTANT_SECTORS = ("Banking", "Healthcare", "IT", "Consumer Defensive")
    SECTOR_ALIASES = {
        "banking": "Banking",
        "financials": "Banking",
        "finance": "Banking",
        "healthcare": "Healthcare",
        "health": "Healthcare",
        "it": "IT",
        "technology": "IT",
        "information technology": "IT",
        "consumer defensive": "Consumer Defensive",
        "consumer defensives": "Consumer Defensive",
        "consumer staples": "Consumer Defensive",
    }
    SEVERITY_WEIGHTS = {"High": 3, "Medium": 2, "Low": 1}
    CATEGORY_PRIORITIES = {
        "Risk": 3,
        "Performance": 3,
        "Concentration": 3,
        "Sector Allocation": 2,
        "Diversification": 2,
        "Portfolio Structure": 2,
        "Income": 1,
        "Valuation": 1,
    }

    def __init__(self) -> None:
        self.portfolio_json: Dict[str, Any] = {}
        self.risk_metrics: Dict[str, Any] = {}
        self.benchmark_metrics: Dict[str, Any] = {}
        self.health_metrics: Dict[str, Any] = {}
        self.strengths: List[Dict[str, Any]] = []
        self.risks: List[Dict[str, Any]] = []
        self.opportunities: List[Dict[str, Any]] = []
        self.action_plan: List[Dict[str, Any]] = []
        self._finding_records: List[Dict[str, Any]] = []

    def analyze(
        self,
        portfolio_json: Optional[Dict[str, Any]],
        risk_metrics: Optional[Dict[str, Any]],
        benchmark_metrics: Optional[Dict[str, Any]],
        health_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a deterministic rule-based opportunity report from analytics outputs."""
        self.portfolio_json = portfolio_json or {}
        self.risk_metrics = risk_metrics or {}
        self.benchmark_metrics = benchmark_metrics or {}
        self.health_metrics = health_metrics or {}
        self.strengths = []
        self.risks = []
        self.opportunities = []
        self.action_plan = []
        self._finding_records = []

        self._check_concentration()
        self._check_holdings()
        self._check_sector_exposure()
        self._check_benchmark()
        self._check_risk()
        self._check_diversification()
        self._check_quality()
        self._check_portfolio_return()

        self._sort_findings()

        return {
            "summary": self._build_summary(),
            "strengths": self.strengths,
            "risks": self.risks,
            "opportunities": self.opportunities,
            "action_plan": self.action_plan,
        }

    def _check_concentration(self) -> None:
        """Assess concentration using top holding, HHI, effective holdings and diversification score."""
        concentration_risk = self.risk_metrics.get("concentration_risk", {})
        top_holding_pct = self._coerce_float(concentration_risk.get("top_holding_weight_pct"))
        hhi = self._coerce_float(concentration_risk.get("hhi"))
        effective_holdings = self._coerce_float(concentration_risk.get("effective_holdings"))
        diversification_score = self._coerce_float(self.risk_metrics.get("diversification", {}).get("score"))

        concentration_score = self._calculate_concentration_score(
            top_holding_pct=top_holding_pct,
            hhi=hhi,
            effective_holdings=effective_holdings,
            diversification_score=diversification_score,
        )
        if concentration_score is None:
            return

        top_holding_name = self._get_top_concentration_name()
        if concentration_score >= 75:
            severity = "High"
            title = f"{top_holding_name} accounts for {top_holding_pct:.2f}% of portfolio value."
            description = (
                "Reason: concentration metrics are elevated across the largest holding, HHI and effective holdings. "
                "Suggested action: trim the position and rebalance into additional holdings. "
                "Expected benefit: reduce single-stock risk and improve diversification."
            )
        elif concentration_score >= 50:
            severity = "Medium"
            title = f"{top_holding_name} is a large position at {top_holding_pct:.2f}% of portfolio value."
            description = (
                "Reason: the portfolio is meaningfully concentrated in one holding. "
                "Suggested action: rebalance gradually into other holdings. "
                "Expected benefit: lower concentration risk and broaden exposure."
            )
        else:
            return

        self._add_finding(
            "risks",
            "Concentration",
            severity,
            title,
            description,
            "Reduce the largest holding and broaden the portfolio.",
            "Lower single-stock risk and improve diversification.",
            top_holding_pct,
            [self._get_primary_symbol()],
            "Concentration",
            "HIGH_CONCENTRATION",
        )

    def _check_holdings(self) -> None:
        """Recommend broader portfolio construction when holdings count is low."""
        holdings = self.portfolio_json.get("holdings", [])
        stock_count = len(holdings)

        if stock_count < self.RULE_THRESHOLDS["minimum_holdings"]:
            self._add_action(
                2,
                "Increase portfolio diversification.",
                f"Increase portfolio holdings to at least {self.RULE_THRESHOLDS['minimum_holdings_target']} holdings and add exposure across multiple sectors.",
                "Improve resilience and reduce idiosyncratic risk.",
            )
            self._add_finding(
                "opportunities",
                "Portfolio Structure",
                "High",
                "Increase the number of holdings.",
                "Reason: the portfolio is narrow and more exposed to stock-specific outcomes.",
                "Expand the portfolio across additional holdings.",
                "Improve resilience and reduce idiosyncratic risk.",
                stock_count,
                [],
                "Portfolio Structure",
                "LOW_HOLDING_COUNT",
            )

    def _check_sector_exposure(self) -> None:
        """Surface overexposure and missing sector diversification opportunities."""
        holdings = self.portfolio_json.get("holdings", [])
        if not holdings:
            return

        sector_allocations: Dict[str, float] = {}
        for holding in holdings:
            sector = self._normalize_sector(holding.get("sector"))
            if not sector:
                continue
            value = self._coerce_float(holding.get("live_value"))
            if value is None:
                continue
            sector_allocations[sector] = sector_allocations.get(sector, 0.0) + value

        if not sector_allocations:
            return

        total_value = sum(sector_allocations.values())
        if total_value <= 0:
            return

        dominant_sector, dominant_value = max(sector_allocations.items(), key=lambda item: item[1])
        dominant_weight_pct = (dominant_value / total_value) * 100.0
        if dominant_weight_pct > self.RULE_THRESHOLDS["sector_exposure_high"]:
            self._add_finding(
                "risks",
                "Sector Allocation",
                "High",
                f"{dominant_sector} accounts for {dominant_weight_pct:.2f}% of portfolio value.",
                "Reason: one sector dominates portfolio value.",
                "Rebalance into underweight sectors.",
                "Reduce sector-specific drawdown risk.",
                round(dominant_weight_pct, 2),
                [self._get_primary_symbol()],
                "Sector Allocation",
                "SECTOR_OVEREXPOSURE",
            )

        missing_sectors = [sector for sector in self.IMPORTANT_SECTORS if sector not in sector_allocations]
        if missing_sectors:
            self._add_action(
                3,
                "Increase sector diversification.",
                f"Add exposure to {', '.join(missing_sectors)} through new holdings or rebalances.",
                "Improve defensive diversification and reduce concentration in existing sectors.",
            )

        for sector in self.IMPORTANT_SECTORS:
            if sector not in sector_allocations:
                self._add_finding(
                    "opportunities",
                    "Sector Allocation",
                    "Medium",
                    f"Add {sector} exposure to improve diversification.",
                    f"Reason: {sector} is not currently represented in the portfolio.",
                    f"Add {sector} exposure through a new holding or reallocation.",
                    "Improve defensive diversification and reduce concentration in existing sectors.",
                    None,
                    [],
                    "Sector Allocation",
                    f"MISSING_{sector.upper().replace(' ', '_')}",
                )

    def _check_benchmark(self) -> None:
        """Translate benchmark-relative performance into structured findings."""
        relative_performance = self._coerce_float(self.benchmark_metrics.get("portfolio_relative_performance_pct"))
        if relative_performance is None:
            return

        if relative_performance < self.RULE_THRESHOLDS["benchmark_underperformance_high"]:
            self._add_finding(
                "risks",
                "Performance",
                "High",
                "Portfolio performance materially trailed the benchmark.",
                "Reason: benchmark-relative performance was worse than -10%.",
                "Review weaker holdings and rebalance toward stronger positions.",
                "Improve benchmark-relative performance.",
                relative_performance,
                [],
                "Performance",
                "UNDERPERFORM_BENCHMARK",
            )
        elif relative_performance < self.RULE_THRESHOLDS["benchmark_underperformance_medium"]:
            self._add_finding(
                "risks",
                "Performance",
                "Medium",
                "Portfolio performance lagged the benchmark.",
                "Reason: benchmark-relative performance was between -5% and -10%.",
                "Review the weakest holdings and rebalance.",
                "Narrow the performance gap.",
                relative_performance,
                [],
                "Performance",
                "UNDERPERFORM_BENCHMARK",
            )
        elif relative_performance > 0.0:
            self._add_finding(
                "strengths",
                "Performance",
                "Low",
                "Portfolio outperformed the benchmark.",
                "Reason: benchmark-relative performance was positive.",
                "Maintain current allocation discipline.",
                "Preserve relative strength.",
                relative_performance,
                [],
                "Performance",
                "OUTPERFORM_BENCHMARK",
            )

        lowest_holding_name = self.benchmark_metrics.get("weakest_stock")
        if lowest_holding_name:
            self._add_action(
                2,
                f"Review {lowest_holding_name} and weak holdings.",
                f"Reduce or replace {lowest_holding_name} and rebalance weak holdings.",
                "Improve benchmark-relative performance.",
            )
            self._add_finding(
                "opportunities",
                "Performance",
                "Medium",
                f"Review {lowest_holding_name}, the weakest benchmark-relative holding.",
                "Reason: the benchmark engine ranked this holding as the weakest performer.",
                "Review the weakest holding and rebalance.",
                "Improve benchmark-relative performance.",
                None,
                [self._get_primary_symbol()],
                "Performance",
                "REVIEW_WEAK_HOLDING",
            )

        overall_rating = self.benchmark_metrics.get("overall_rating")
        performance_summary = self.benchmark_metrics.get("performance_summary", {})
        if overall_rating and str(overall_rating).lower() in {"poor", "weak"}:
            self._add_finding(
                "risks",
                "Performance",
                "Medium",
                f"Benchmark ranking is {overall_rating}.",
                "Reason: the benchmark engine rated the portfolio as weak.",
                "Prioritize the weakest holdings and reduce lagging exposure.",
                "Improve portfolio ranking.",
                overall_rating,
                [],
                "Performance",
                "WEAK_BENCHMARK_RATING",
            )
        elif performance_summary.get("portfolio_strength") and str(performance_summary.get("portfolio_strength")).lower() in {"strong", "good"}:
            self._add_finding(
                "strengths",
                "Performance",
                "Low",
                "Benchmark portfolio strength is positive.",
                "Reason: the benchmark engine reported solid portfolio strength.",
                "Maintain current allocation discipline.",
                "Sustain relative performance.",
                performance_summary.get("portfolio_strength"),
                [],
                "Performance",
                "STRONG_BENCHMARK_RATING",
            )

    def _check_risk(self) -> None:
        """Translate risk summary, contributions and stress-test results into findings."""
        risk_summary = self.risk_metrics.get("risk_summary", {})
        sharpe_ratio = self._coerce_float(risk_summary.get("sharpe_ratio"))
        risk_score = self._coerce_float(risk_summary.get("risk_score"))
        beta = self._coerce_float(risk_summary.get("portfolio_beta"))
        var_value = self._coerce_float(risk_summary.get("daily_var", {}).get("percent"))
        drawdown = self._coerce_float(risk_summary.get("max_drawdown", {}).get("percent"))

        if sharpe_ratio is not None and sharpe_ratio < 0.0:
            self._add_finding(
                "risks",
                "Risk",
                "Medium",
                "Negative Sharpe ratio.",
                "Reason: returns have not compensated for portfolio risk.",
                "Review weaker holdings and improve return quality.",
                "Improve risk-adjusted returns.",
                sharpe_ratio,
                [self._get_primary_symbol()],
                "Risk",
                "NEGATIVE_SHARPE",
            )

        if risk_score is not None and risk_score > self.RULE_THRESHOLDS["risk_score_high"]:
            self._add_finding(
                "risks",
                "Risk",
                "High",
                "Overall portfolio risk is elevated.",
                "Reason: the risk score is above the high-risk threshold.",
                "Reduce risky exposures and rebalance toward lower-beta holdings.",
                "Improve portfolio resilience.",
                risk_score,
                [self._get_primary_symbol()],
                "Risk",
                "HIGH_RISK_SCORE",
            )

        if beta is not None and beta > self.RULE_THRESHOLDS["beta_high"]:
            self._add_finding(
                "risks",
                "Risk",
                "Medium",
                "Portfolio beta is above 1.2.",
                "Reason: the portfolio is more sensitive to market swings.",
                "Reduce high-beta exposure.",
                "Lower market sensitivity.",
                beta,
                [self._get_primary_symbol()],
                "Risk",
                "HIGH_BETA",
            )
        elif beta is not None and beta < self.RULE_THRESHOLDS["beta_low"]:
            self._add_finding(
                "strengths",
                "Risk",
                "Low",
                "Portfolio beta is below 1.0.",
                "Reason: the portfolio is less sensitive to the broader market.",
                "Preserve the current risk posture.",
                "Maintain downside resilience.",
                beta,
                [],
                "Risk",
                "LOW_BETA",
            )

        if var_value is not None and var_value > self.RULE_THRESHOLDS["var_high"]:
            self._add_finding(
                "risks",
                "Risk",
                "Medium",
                "Value-at-risk is elevated.",
                "Reason: downside risk on the measured horizon is relatively high.",
                "Trim high-risk holdings.",
                "Reduce expected drawdown.",
                var_value,
                [self._get_primary_symbol()],
                "Risk",
                "HIGH_VAR",
            )

        if drawdown is not None and drawdown > self.RULE_THRESHOLDS["drawdown_high"]:
            self._add_finding(
                "risks",
                "Risk",
                "High",
                "Maximum drawdown is elevated.",
                "Reason: the portfolio has experienced a significant drawdown.",
                "Review the largest contributors to drawdown.",
                "Improve stability.",
                drawdown,
                [self._get_primary_symbol()],
                "Risk",
                "HIGH_DRAWDOWN",
            )

        risk_contributions = self.risk_metrics.get("risk_contributions", {})
        if risk_contributions:
            dominant_symbol = max(risk_contributions, key=risk_contributions.get)
            dominant_contribution = self._coerce_float(risk_contributions.get(dominant_symbol))
            if dominant_contribution is not None and dominant_contribution >= self.RULE_THRESHOLDS["risk_contribution_high"]:
                holding_name = self._get_holding_name(dominant_symbol)
                self._add_finding(
                    "risks",
                    "Risk",
                    "Medium",
                    f"{holding_name} is the largest driver of portfolio risk.",
                    "Reason: the holding contributes more than half of portfolio risk.",
                    "Review position sizing and reduce the dominant risk contributor.",
                    "Reduce concentration of risk.",
                    round(dominant_contribution * 100.0, 2),
                    [dominant_symbol],
                    "Risk",
                    "LARGEST_RISK_CONTRIBUTOR",
                )

        holding_summary = self.risk_metrics.get("holding_summary", {})
        worst_performing_stock = holding_summary.get("worst_performing_stock")
        if worst_performing_stock:
            self._add_action(
                2,
                f"Review {self._get_holding_name(worst_performing_stock)} and weak holdings.",
                f"Reduce or replace {self._get_holding_name(worst_performing_stock)} and rebalance weak holdings.",
                "Improve portfolio resilience and return profile.",
            )
            self._add_finding(
                "opportunities",
                "Risk",
                "Medium",
                f"Review {self._get_holding_name(worst_performing_stock)} as the weakest holding.",
                "Reason: the holding summary marks this stock as the worst performer.",
                "Trim or replace the weakest holding.",
                "Improve portfolio resilience and return profile.",
                worst_performing_stock,
                [worst_performing_stock],
                "Risk",
                "REVIEW_WORST_HOLDING",
            )

        stress_test = self.risk_metrics.get("stress_test", {})
        if stress_test:
            worst_stress = None
            for scenario in stress_test.values():
                scenario_return = self._coerce_float(scenario.get("portfolio_return_pct"))
                if scenario_return is None:
                    continue
                if worst_stress is None or scenario_return < worst_stress:
                    worst_stress = scenario_return
            if worst_stress is not None and worst_stress < self.RULE_THRESHOLDS["stress_test_threshold"]:
                self._add_finding(
                    "risks",
                    "Risk",
                    "Medium",
                    "Stress tests show material downside sensitivity.",
                    "Reason: the portfolio underperforms significantly in adverse scenarios.",
                    "Reduce exposure to fragile positions.",
                    "Improve resilience under stress.",
                    worst_stress,
                    [self._get_primary_symbol()],
                    "Risk",
                    "STRESS_TEST_DOWNSIDE",
                )

    def _check_diversification(self) -> None:
        """Create findings based on diversification score and correlation behavior."""
        diversification_metrics = self.risk_metrics.get("diversification", {})
        diversification_score = self._coerce_float(
            diversification_metrics.get("overall_score") if diversification_metrics.get("overall_score") is not None else diversification_metrics.get("score")
        )
        average_correlation = self._coerce_float(self.risk_metrics.get("correlation", {}).get("average"))

        if diversification_score is not None and diversification_score > self.RULE_THRESHOLDS["diversification_high"]:
            self._add_finding(
                "strengths",
                "Diversification",
                "Low",
                "Diversification score is strong.",
                "Reason: the portfolio is spread across multiple holdings and sectors.",
                "Preserve the current diversification posture.",
                "Maintain resilience.",
                diversification_score,
                [],
                "Diversification",
                "STRONG_DIVERSIFICATION",
            )
        elif diversification_score is not None and diversification_score < self.RULE_THRESHOLDS["diversification_low"]:
            self._add_action(
                3,
                "Improve diversification.",
                "Add exposure across more holdings or sectors.",
                "Lower common-factor risk.",
            )
            self._add_finding(
                "opportunities",
                "Diversification",
                "Medium",
                "Improve diversification.",
                "Reason: the diversification score is below the desired level.",
                "Add exposure across more holdings or sectors.",
                "Lower common-factor risk.",
                diversification_score,
                [],
                "Diversification",
                "LOW_DIVERSIFICATION",
            )

        if average_correlation is not None and average_correlation > 0.7:
            self._add_finding(
                "risks",
                "Diversification",
                "Medium",
                "Average correlation is high.",
                "Reason: holdings tend to move together.",
                "Add lower-correlation holdings.",
                "Improve diversification.",
                average_correlation,
                [self._get_primary_symbol()],
                "Diversification",
                "HIGH_CORRELATION",
            )

    def _check_quality(self) -> None:
        """Evaluate holding quality using dividend yield, valuation and sector-aware P/E thresholds."""
        holdings = self.portfolio_json.get("holdings", [])

        for holding in sorted(holdings, key=lambda item: str(item.get("symbol") or item.get("ticker") or "")):
            dividend_yield = self._coerce_float(holding.get("dividend_yield"))
            pe_ratio = self._coerce_float(holding.get("pe_ratio"))
            symbol = str(holding.get("symbol") or holding.get("ticker") or "Holding")
            holding_name = self._get_holding_name(symbol)
            sector = self._normalize_sector(holding.get("sector"))

            if dividend_yield is not None and dividend_yield > self.RULE_THRESHOLDS["dividend_high"]:
                self._add_finding(
                    "strengths",
                    "Income",
                    "Low",
                    f"{holding_name} offers an attractive dividend yield.",
                    "Reason: the holding provides a relatively high income stream.",
                    "Maintain the position if income is a priority.",
                    "Support portfolio income.",
                    dividend_yield,
                    [symbol],
                    "Income",
                    "HIGH_DIVIDEND",
                )
            elif dividend_yield is not None and dividend_yield >= 2.0:
                self._add_finding(
                    "strengths",
                    "Income",
                    "Low",
                    f"{holding_name} provides moderate income.",
                    "Reason: the holding offers a steady dividend yield.",
                    "Consider holding if income stability is desired.",
                    "Support portfolio income.",
                    dividend_yield,
                    [symbol],
                    "Income",
                    "MODERATE_DIVIDEND",
                )

            market_cap = self._coerce_float(holding.get("market_cap"))
            if market_cap is not None:
                market_cap_billion = market_cap / 1e9
                if market_cap_billion < 20 and pe_ratio is not None and pe_ratio < thresholds["fair"]:
                    self._add_finding(
                        "opportunities",
                        "Valuation",
                        "Medium",
                        f"{holding_name} is a small-cap value candidate.",
                        "Reason: the company has a smaller market cap with reasonable valuation.",
                        "Review growth prospects and sector positioning.",
                        "Potential value opportunity.",
                        market_cap,
                        [symbol],
                        "Valuation",
                        "SMALL_CAP_VALUE",
                    )
                elif market_cap_billion >= 200 and dividend_yield is not None and dividend_yield >= 2.0:
                    self._add_finding(
                        "strengths",
                        "Income",
                        "Low",
                        f"{holding_name} combines large-cap stability with income.",
                        "Reason: the holding is large-cap and offers steady yield.",
                        "Keep exposure if stability is a priority.",
                        "Support portfolio resilience.",
                        market_cap,
                        [symbol],
                        "Income",
                        "LARGE_CAP_INCOME",
                    )

            if pe_ratio is None:
                continue

            thresholds = self.VALUATION_THRESHOLDS.get(
                sector,
                self.VALUATION_THRESHOLDS["default"],
            )

            if pe_ratio < thresholds["deep_value"]:
                self._add_finding(
                    "opportunities",
                    "Valuation",
                    "High",
                    f"{holding_name} appears deeply undervalued.",
                    "Reason: valuation is well below the normal market range.",
                    "Verify business fundamentals before increasing exposure.",
                    "Potential valuation upside.",
                    pe_ratio,
                    [symbol],
                    "Valuation",
                    "DEEP_VALUE",
                )
            elif pe_ratio < thresholds["value"]:
                self._add_finding(
                    "opportunities",
                    "Valuation",
                    "Medium",
                    f"{holding_name} appears reasonably valued.",
                    "Reason: valuation is below the market average.",
                    "Monitor for accumulation opportunities.",
                    "Potential long-term upside.",
                    pe_ratio,
                    [symbol],
                    "Valuation",
                    "VALUE_STOCK",
                )
            elif pe_ratio > thresholds["growth"]:
                severity = "Medium"
                if sector in {"Banking", "Healthcare", "IT"}:
                    severity = "High"
                self._add_finding(
                    "risks",
                    "Valuation",
                    severity,
                    f"{holding_name} trades at an elevated valuation for its sector.",
                    "Reason: price-to-earnings ratio is above the expected range for its sector.",
                    "Review whether future earnings justify the premium.",
                    "Reduce valuation risk.",
                    pe_ratio,
                    [symbol],
                    "Valuation",
                    "HIGH_VALUATION",
                )

    def _check_portfolio_return(self) -> None:
        """Use benchmark-return data to flag underperforming portfolio behavior."""
        portfolio_return = self._coerce_float(self.benchmark_metrics.get("portfolio_weighted_return_pct"))
        if portfolio_return is None:
            return

        if portfolio_return < 0.0:
            self._add_action(
                2,
                "Review underperforming holdings.",
                "Trim or replace the weakest holdings and rebalance toward stronger performers.",
                "Improve overall portfolio performance.",
            )
            self._add_finding(
                "opportunities",
                "Performance",
                "Medium",
                "Review the portfolio's underperforming holdings.",
                "Reason: the benchmark engine reports negative portfolio-weighted return.",
                "Review the weakest holdings and rebalance.",
                "Improve overall portfolio performance.",
                portfolio_return,
                [],
                "Performance",
                "UNDERPERFORMING_HOLDINGS",
            )

    def _add_finding(
        self,
        bucket: str,
        category: str,
        severity: str,
        title: str,
        reason: str,
        recommendation: str,
        expected_benefit: str,
        metric: Optional[Any] = None,
        related_symbols: Optional[List[str]] = None,
        theme: Optional[str] = None,
        finding_id: Optional[str] = None,
    ) -> None:
        """Append a normalized finding to the requested structured bucket."""
        if bucket == "strengths":
            target = self.strengths
        elif bucket == "risks":
            target = self.risks
        elif bucket == "opportunities":
            target = self.opportunities
        else:
            raise ValueError(f"Unsupported finding bucket: {bucket}")

        priority = self._priority_for(category, severity)
        finding = {
            "id": finding_id or self._fallback_id(category),
            "theme": theme or category,
            "category": category,
            "severity": severity,
            "priority": priority,
            "title": title,
            "reason": reason,
            "recommendation": recommendation,
            "expected_benefit": expected_benefit,
            "metric": metric,
            "related_symbols": related_symbols or [],
        }
        if finding.get("id"):
            for existing in self._finding_records:
                if existing.get("id") == finding.get("id") and existing.get("bucket") == bucket:
                    return
        target.append(finding)
        self._finding_records.append({"bucket": bucket, **finding})

    def _add_action(self, priority: int, title: str, action: str, expected_benefit: str) -> None:
        """Append a deterministic action plan entry while avoiding duplicates and keeping the list compact."""
        normalized_title = title.strip()
        for existing in self.action_plan:
            if existing.get("title") == normalized_title:
                return

        self.action_plan.append(
            {
                "priority": priority,
                "title": normalized_title,
                "action": action,
                "expected_benefit": expected_benefit,
            }
        )
        self.action_plan = sorted(self.action_plan, key=lambda item: (item.get("priority", 99), item.get("title", "")))[:5]

    def _build_summary(self) -> Dict[str, Any]:
        """Aggregate findings into a compact summary for downstream consumers."""
        strength_count = len(self.strengths)
        risk_count = len(self.risks)
        opportunity_count = len(self.opportunities)
        action_count = len(self.action_plan)
        weighted_score = sum(
            self.SEVERITY_WEIGHTS.get(finding.get("severity"), 0) * self.CATEGORY_PRIORITIES.get(finding.get("category"), 1)
            for finding in self._finding_records
        )

        if any(finding.get("bucket") == "risks" and finding.get("severity") == "High" for finding in self._finding_records):
            overall_status = "High Improvement Potential"
        elif weighted_score >= 10 or risk_count >= 4 or opportunity_count >= 4:
            overall_status = "Needs Improvement"
        elif strength_count >= 3 and risk_count <= 1:
            overall_status = "Excellent"
        elif strength_count >= 2 and risk_count <= 2:
            overall_status = "Good"
        else:
            overall_status = "Moderate"

        highest_priority_issue = ""
        if self.risks:
            highest_priority_issue = self.risks[0]["title"]
        elif self.opportunities:
            highest_priority_issue = self.opportunities[0]["title"]

        key_strength = ""
        if self.strengths:
            key_strength = self.strengths[0]["title"]

        top_recommendation = ""
        if self.action_plan:
            top_recommendation = self.action_plan[0]["title"]

        return {
            "overall_status": overall_status,
            "strength_count": strength_count,
            "risk_count": risk_count,
            "opportunity_count": opportunity_count,
            "action_count": action_count,
            "highest_priority_issue": highest_priority_issue,
            "key_strength": key_strength,
            "top_recommendation": top_recommendation,
            "finding_counts": {
                "strengths": strength_count,
                "risks": risk_count,
                "opportunities": opportunity_count,
                "actions": action_count,
            },
        }

    def _calculate_concentration_score(
        self,
        top_holding_pct: Optional[float],
        hhi: Optional[float],
        effective_holdings: Optional[float],
        diversification_score: Optional[float],
    ) -> Optional[float]:
        """Combine concentration inputs into a single severity score."""
        if top_holding_pct is None and hhi is None and effective_holdings is None and diversification_score is None:
            return None

        top_component = 20.0
        if top_holding_pct is not None:
            if top_holding_pct >= 60.0:
                top_component = 100.0
            elif top_holding_pct >= 50.0:
                top_component = 80.0
            elif top_holding_pct >= 40.0:
                top_component = 60.0
            elif top_holding_pct >= 30.0:
                top_component = 40.0

        hhi_component = 20.0
        if hhi is not None:
            if hhi >= 0.70:
                hhi_component = 100.0
            elif hhi >= 0.60:
                hhi_component = 80.0
            elif hhi >= 0.50:
                hhi_component = 70.0
            elif hhi >= 0.40:
                hhi_component = 50.0

        effective_component = 20.0
        if effective_holdings is not None:
            if effective_holdings < 2.0:
                effective_component = 100.0
            elif effective_holdings < 3.0:
                effective_component = 80.0
            elif effective_holdings < 5.0:
                effective_component = 60.0
            elif effective_holdings < 7.0:
                effective_component = 40.0

        diversification_component = 20.0
        if diversification_score is not None:
            if diversification_score < 40.0:
                diversification_component = 100.0
            elif diversification_score < 60.0:
                diversification_component = 80.0
            elif diversification_score < 80.0:
                diversification_component = 60.0
            elif diversification_score < 90.0:
                diversification_component = 40.0

        return round((0.35 * top_component) + (0.25 * hhi_component) + (0.20 * effective_component) + (0.20 * diversification_component), 2)

    def _get_top_concentration_name(self) -> str:
        """Return the company name associated with the largest concentration."""
        holding_analysis = self.risk_metrics.get("holding_analysis", [])
        if holding_analysis:
            top_entry = max(holding_analysis, key=lambda item: self._coerce_float(item.get("weight_pct")) or 0.0)
            if top_entry.get("company"):
                return str(top_entry.get("company"))
            if top_entry.get("symbol"):
                return str(top_entry.get("symbol"))
        for holding in self.portfolio_json.get("holdings", []):
            if holding.get("stock_name"):
                return str(holding.get("stock_name"))
        return "The largest holding"

    def _get_holding_name(self, symbol: str) -> str:
        """Resolve a holding symbol to a company name using the available analytics."""
        for holding in self.portfolio_json.get("holdings", []):
            if holding.get("symbol") == symbol:
                return str(holding.get("stock_name") or symbol)
        for analysis in self.risk_metrics.get("holding_analysis", []):
            if analysis.get("symbol") == symbol:
                return str(analysis.get("company") or symbol)
        return symbol

    def _get_primary_symbol(self) -> str:
        for holding in self.portfolio_json.get("holdings", []):
            symbol = holding.get("symbol")
            if symbol:
                return str(symbol)
        return ""

    def _fallback_id(self, category: str) -> str:
        return f"{category.upper().replace(' ', '_')}_FALLBACK"

    def _sort_findings(self) -> None:
        """Sort structured outputs by priority and severity for deterministic downstream use."""
        self.strengths = sorted(self.strengths, key=lambda item: (item.get("priority", 99), self._severity_rank(item.get("severity"))))
        self.risks = sorted(self.risks, key=lambda item: (item.get("priority", 99), self._severity_rank(item.get("severity"))))
        self.opportunities = sorted(self.opportunities, key=lambda item: (item.get("priority", 99), self._severity_rank(item.get("severity"))))
        self.action_plan = sorted(self.action_plan, key=lambda item: (item.get("priority", 99), item.get("title", "")))

    def _severity_rank(self, severity: Optional[str]) -> int:
        return {"High": 0, "Medium": 1, "Low": 2}.get(str(severity or "").strip(), 3)

    def _priority_for(self, category: str, severity: str) -> int:
        base_priority = self.CATEGORY_PRIORITIES.get(category, 1)
        severity_adjustment = 0 if severity == "High" else 1 if severity == "Medium" else 2
        return base_priority + severity_adjustment

    def _coerce_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _normalize_sector(self, sector: Any) -> str:
        if sector is None:
            return ""
        normalized = str(sector).strip()
        if not normalized:
            return ""
        lowered = normalized.lower()
        for alias, canonical in self.SECTOR_ALIASES.items():
            if lowered == alias or lowered == canonical.lower():
                return canonical
        return normalized
