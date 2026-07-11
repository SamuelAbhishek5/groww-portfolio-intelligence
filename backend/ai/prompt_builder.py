import logging

from typing import Any, Dict, List, Optional

from backend.ai.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Build a compact, information-rich prompt from deterministic analytics outputs."""

    MAX_PROMPT_HOLDINGS = 10

    def __init__(self) -> None:
        self.system_prompt = SYSTEM_PROMPT
        self.user_template = USER_PROMPT_TEMPLATE

    def build_system_prompt(self) -> str:
        return self.system_prompt

    def build_prompt(
        self,
        portfolio_json: Optional[Dict[str, Any]] = None,
        risk_metrics: Optional[Dict[str, Any]] = None,
        health_metrics: Optional[Dict[str, Any]] = None,
        benchmark_metrics: Optional[Dict[str, Any]] = None,
        opportunity_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        portfolio_json = portfolio_json or {}
        risk_metrics = risk_metrics or {}
        health_metrics = health_metrics or {}
        benchmark_metrics = benchmark_metrics or {}
        opportunity_result = opportunity_result or {}

        portfolio_summary = portfolio_json.get("summary", {}) or {}
        holdings = list(portfolio_json.get("holdings", []) or [])
        risk_summary = risk_metrics.get("risk_summary", {}) or {}
        concentration_risk = risk_metrics.get("concentration_risk", {}) or {}
        diversification = risk_metrics.get("diversification", {}) or {}
        correlation = risk_metrics.get("correlation", {}) or {}
        stress_test = risk_metrics.get("stress_test", {}) or {}
        holding_analysis = list(risk_metrics.get("holding_analysis", []) or [])
        portfolio_health = health_metrics.get("portfolio_health", {}) or {}
        
        sections: List[str] = ["Portfolio insight request", ""]
        sections.extend(self._build_portfolio_snapshot(portfolio_summary, holdings))
        sections.extend(self._build_portfolio_composition(holdings))
        sections.extend(self._build_risk_section(risk_metrics, risk_summary))
        sections.extend(self._build_diversification_section(concentration_risk, diversification, correlation))
        sections.extend(self._build_correlation_section(correlation))
        sections.extend(self._build_stress_section(stress_test))
        sections.extend(self._build_health_section(portfolio_health))
        sections.extend(self._build_benchmark_section(benchmark_metrics))
        sections.extend(self._build_opportunity_section(opportunity_result))
        sections.extend(self._build_holding_analysis(holding_analysis))
        sections.extend(self._build_instruction_section())
        
        return "\n".join(sections)

    def _build_portfolio_snapshot(self, portfolio_summary: Dict[str, Any], holdings: List[Dict[str, Any]]) -> List[str]:
        sections = ["# Portfolio Snapshot", "Portfolio Overview"]
        investment = self._coerce_float(portfolio_summary.get("total_invested_value"))
        current_value = self._coerce_float(portfolio_summary.get("total_live_value"))
        unrealized_pnl = self._coerce_float(portfolio_summary.get("total_unrealised_pnl"))
        overall_return = portfolio_summary.get("overall_return_pct")
        if overall_return is None and investment not in (None, 0.0):
            overall_return = ((current_value or 0.0) - investment) / investment * 100.0 if current_value is not None else None
            
        sections.append("Note: 'Overall return' is since inception, which may differ from benchmark lookback periods.")
        sections.append(f"- Total investment (Amount invested): {self._format_currency(investment)}")
        sections.append(f"- Current value: {self._format_currency(current_value)}")
        sections.append(f"- Absolute Unrealized PnL: {self._format_currency(unrealized_pnl)}")
        sections.append(f"- Overall Percentage Return: {self._format_percent(overall_return)}")
        sections.append(f"- Holdings: {len(holdings)}")
        return sections

    def _build_portfolio_composition(self, holdings: List[Dict[str, Any]]) -> List[str]:
        sections = ["", "# Portfolio Composition", "Portfolio Composition"]
        holdings_to_show = holdings[: self.MAX_PROMPT_HOLDINGS]
        if not holdings_to_show:
            sections.append("- No holdings available.")
            return sections
        for holding in holdings_to_show:
            company = self._string_or_default(holding.get("stock_name"), "N/A")
            symbol = self._string_or_default(holding.get("symbol"), "N/A")
            sector = self._string_or_default(holding.get("sector"), "N/A")
            industry = self._string_or_default(holding.get("industry"), "N/A")
            quantity = self._format_number(holding.get("quantity"))
            live_value = self._format_currency(holding.get("live_value"))
            pe_ratio = self._format_ratio(holding.get("pe_ratio"))
            dividend_yield = self._format_percent(holding.get("dividend_yield"))
            market_cap = self._format_currency(holding.get("market_cap"))
            sections.append(
                f"- {company} | Symbol: {symbol} | Sector: {sector} | Industry: {industry} | Qty: {quantity} | "
                f"Live value: {live_value} | PE: {pe_ratio} | Dividend yield: {dividend_yield} | Market cap: {market_cap}"
            )
        return sections

    def _build_risk_section(self, risk_metrics: Dict[str, Any], risk_summary: Dict[str, Any]) -> List[str]:
        sections = ["", "# Risk Analysis", "Risk Score Interpretation: 0-20=Very Low, 20-40=Low, 40-60=Moderate, 60-80=High, 80-100=Very High (Higher = Safer)"]
        sections.append(
            f"- Risk score: {self._format_ratio(risk_summary.get('risk_score'))}; "
            f"Risk level: {self._string_or_default(risk_summary.get('risk_level'), 'N/A')}; "
            f"Portfolio beta: {self._format_ratio(risk_summary.get('portfolio_beta'))}"
        )
        sections.append(
            f"- Volatility: {self._format_percent(self._nested_nested_value(risk_summary, 'volatility', 'value_pct'))}; "
            f"Daily VaR: {self._format_percent(self._nested_nested_value(risk_summary, 'daily_var', 'percent'))}; "
            f"Expected shortfall: {self._format_percent(self._nested_nested_value(risk_summary, 'expected_shortfall', 'percent'))}"
        )
        sections.append(
            f"- Maximum drawdown: {self._format_percent(self._nested_nested_value(risk_summary, 'max_drawdown', 'percent'))}; "
            f"Rolling volatility: {self._format_percent(self._nested_nested_value(risk_summary, 'rolling_volatility_30d', 'value_pct'))}; "
            f"Sharpe ratio: {self._format_ratio(risk_summary.get('sharpe_ratio'))}"
        )
        
        # Risk Contributors Summary
        holding_analysis = risk_metrics.get("holding_analysis", [])
        if holding_analysis:
            sorted_by_risk = sorted(holding_analysis, key=lambda x: self._coerce_float(x.get("risk_contribution_pct")) or 0.0, reverse=True)
            if sorted_by_risk:
                top_risk = sorted_by_risk[0]
                sections.append(f"- Highest risk contributor: {top_risk.get('symbol', 'N/A')} ({self._format_percent(top_risk.get('risk_contribution_pct'))})")
            if len(sorted_by_risk) > 1:
                sec_risk = sorted_by_risk[1]
                sections.append(f"- Second risk contributor: {sec_risk.get('symbol', 'N/A')} ({self._format_percent(sec_risk.get('risk_contribution_pct'))})")

        highlights = risk_metrics.get("insights") or []
        sections.append(f"- Risk highlights: {self._join_items(highlights)}")
        return sections

    def _build_diversification_section(
        self,
        concentration_risk: Dict[str, Any],
        diversification: Dict[str, Any],
        correlation: Dict[str, Any],
    ) -> List[str]:
        sections = ["", "# Diversification & Concentration", "Diversification Method: Combined Correlation & Structural scores."]
        sections.append(
            f"- Diversification score: {self._format_ratio(diversification.get('score'))}; "
            f"Stock count: {self._format_number(diversification.get('stock_count'))}; "
            f"Sector count: {self._format_number(diversification.get('sector_count'))}"
        )
        
        sections.append("Concentration Interpretation: HHI > 0.25 = Highly concentrated. Effective Holdings Ideal = 8+.")
        sections.append(
            f"- Top holding concentration: {self._format_percent(concentration_risk.get('top_holding_weight_pct'))}; "
            f"Top sector: {self._string_or_default(concentration_risk.get('top_sector'), 'N/A')}; "
            f"HHI: {self._format_ratio(concentration_risk.get('hhi'))}; "
            f"Effective holdings: {self._format_ratio(concentration_risk.get('effective_holdings'))}"
        )
        return sections

    def _build_correlation_section(self, correlation: Dict[str, Any]) -> List[str]:
        sections = ["", "# Correlation", "Correlation Interpretation: <0.3 Excellent, 0.3-0.6 Moderate, >0.7 High"]
        sections.append(f"- Average correlation: {self._format_ratio(correlation.get('average'))}")
        
        highest_pair = correlation.get("highest_pair") or []
        if isinstance(highest_pair, list) and len(highest_pair) >= 3:
            pair_text = f"{highest_pair[0]}-{highest_pair[1]} ({self._format_ratio(highest_pair[2])})"
        else:
            pair_text = "N/A"
        sections.append(
            f"- Highest correlated pair: {pair_text}; "
            f"Ticker count: {self._format_number(correlation.get('ticker_count'))}"
        )
        return sections

    def _build_stress_section(self, stress_test: Dict[str, Any]) -> List[str]:
        sections = ["", "# Stress Tests", "Stress Tests"]
        # Fixed dictionary keys based on analytics output
        for scenario_name, scenario_key in (
            ("Market Correction", "market_correction"),
            ("Credit Shock", "credit_shock"),
            ("Tech Drawdown", "tech_drawdown"),
        ):
            scenario = stress_test.get(scenario_key) or {}
            portfolio_return = scenario.get("portfolio_return_pct")
            sections.append(f"- {scenario_name}: {self._format_percent(portfolio_return)}")
        return sections

    def _build_health_section(self, portfolio_health: Dict[str, Any]) -> List[str]:
        sections = ["", "# Portfolio Health", "Portfolio Health Method: Overall = 30% Risk + 20% Diversification + 20% Performance + 10% Concentration + 10% Quality + 10% Stability"]
        breakdown = portfolio_health.get("breakdown") or {}
        strongest = self._format_dimension_rank(breakdown, descending=True)
        weakest = self._format_dimension_rank(breakdown, descending=False)
        sections.append(
            f"- Overall score: {self._format_ratio(portfolio_health.get('overall_score'))}; "
            f"Grade: {self._string_or_default(portfolio_health.get('grade'), 'N/A')}; "
            f"Status: {self._string_or_default(portfolio_health.get('status'), 'N/A')}"
        )
        sections.append(f"- Breakdown (Unweighted): {self._join_mapping(breakdown)}")
        sections.append(f"- Strongest dimensions: {strongest}")
        sections.append(f"- Weakest dimensions: {weakest}")
        sections.append(f"- Strengths: {self._join_items(portfolio_health.get('strengths') or [])}")
        sections.append(f"- Weaknesses: {self._join_items(portfolio_health.get('weaknesses') or [])}")
        return sections

    def _build_benchmark_section(self, benchmark_metrics: Dict[str, Any]) -> List[str]:
        sections = ["", "# Benchmark Comparison", "Benchmark Summary"]
        sections.append(
            f"- Benchmark name: {self._string_or_default(benchmark_metrics.get('benchmark_name'), 'N/A')}; "
            f"Lookback period: {self._string_or_default(benchmark_metrics.get('lookback_period'), 'N/A')}"
        )
        sections.append(
            f"- Benchmark return: {self._format_percent(benchmark_metrics.get('benchmark_return_pct'))}; "
            f"Portfolio return (Benchmark Period): {self._format_percent(benchmark_metrics.get('portfolio_weighted_return_pct'))}; "
            f"Relative performance: {self._format_percent(benchmark_metrics.get('portfolio_relative_performance_pct'))}; "
        )
        sections.append(
            f"- Alpha: {self._format_ratio(benchmark_metrics.get('alpha_pct'))}; "
            f"Tracking Error: {self._format_percent(benchmark_metrics.get('tracking_error_pct'))}; "
            f"Information Ratio: {self._format_ratio(benchmark_metrics.get('information_ratio'))}; "
            f"Overall rating: {self._string_or_default(benchmark_metrics.get('overall_rating'), 'N/A')}"
        )
        
        comparison = []
        for item in benchmark_metrics.get("holdings", [])[: self.MAX_PROMPT_HOLDINGS]:
            name = self._string_or_default(item.get("stock_name") or item.get("symbol"), "N/A")
            comparison.append(
                f"{name}: return {self._format_percent(item.get('stock_return_pct'))}; "
                f"relative {self._format_percent(item.get('relative_performance_pct'))}; "
            )
        sections.append(f"- Holding comparison: {'; '.join(comparison) if comparison else 'N/A'}")
        return sections

    def _build_opportunity_section(self, opportunity_result: Dict[str, Any]) -> List[str]:
        sections = ["", "# Opportunity Analysis", "Portfolio Opportunities"]
     
        summary = opportunity_result.get("summary", {})
        sections.append(f"- Overall status: {self._string_or_default(summary.get('overall_status'), 'N/A')}")
        
        highest_priority_issue = summary.get('highest_priority_issue') or "N/A"
        top_recommendation = summary.get('top_recommendation') or "N/A"
        
        sections.append(f"- Highest Priority Issue: {highest_priority_issue}")
        sections.append(f"- Highest Priority Recommendation: {top_recommendation}")
        
        sections.append(f"- Strengths: {self._join_items(opportunity_result.get('strengths') or [])}")
        sections.append(f"- Risks: {self._join_items(opportunity_result.get('risks') or [])}")
        sections.append(f"- Opportunities: {self._join_items(opportunity_result.get('opportunities') or [])}")
        sections.append(f"- Recommended actions: {self._join_items(opportunity_result.get('action_plan') or opportunity_result.get('recommended_actions') or [])}")
        
        return sections

    def _build_holding_analysis(self, holding_analysis: List[Dict[str, Any]]) -> List[str]:
        sections = ["", "# Holding Analysis", "Holding Analysis"]
        sorted_holdings = sorted(
            holding_analysis,
            key=lambda item: self._coerce_float(item.get("weight_pct")) or 0.0,
            reverse=True,
        )
        
        if not sorted_holdings:
            sections.append("- No holding analysis available.")
            return sections
            
        # Top level holding metrics facts
        if len(sorted_holdings) > 0:
            highest_beta = max(sorted_holdings, key=lambda x: self._coerce_float(x.get("beta")) or -999)
            highest_vol = max(sorted_holdings, key=lambda x: self._coerce_float(x.get("volatility_pct")) or -999)
            max_drawdown = min(sorted_holdings, key=lambda x: self._coerce_float(x.get("max_drawdown_pct")) or 999)
            
            sections.append(f"- Largest holding: {sorted_holdings[0].get('symbol', 'N/A')}")
            sections.append(f"- Highest beta holding: {highest_beta.get('symbol', 'N/A')} ({self._format_ratio(highest_beta.get('beta'))})")
            sections.append(f"- Highest volatility holding: {highest_vol.get('symbol', 'N/A')} ({self._format_percent(highest_vol.get('volatility_pct'))})")
            sections.append(f"- Worst drawdown holding: {max_drawdown.get('symbol', 'N/A')} ({self._format_percent(max_drawdown.get('max_drawdown_pct'))})")

        sections.append("\nDetailed Holding Data:")
        for item in sorted_holdings[: self.MAX_PROMPT_HOLDINGS]:
            company = self._string_or_default(item.get("company") or item.get("company_name") or item.get("symbol"), "N/A")
            symbol = self._string_or_default(item.get("symbol"), "N/A")
            sector = self._string_or_default(item.get("sector"), "N/A")
            sections.append(
                f"- {company} ({symbol}) | Sector: {sector} | Weight: {self._format_percent(item.get('weight_pct'))} | "
                f"Risk score: {self._format_ratio(item.get('risk_score'))} | Beta: {self._format_ratio(item.get('beta'))} | "
                f"Volatility: {self._format_percent(item.get('volatility_pct'))} | Sharpe: {self._format_ratio(item.get('sharpe'))} | "
                f"Risk contribution: {self._format_percent(item.get('risk_contribution_pct'))}"
            )
        return sections

    def _build_instruction_section(self) -> List[str]:
        sections = ["", "# System Instructions & Constraints", "CRITICAL INSTRUCTIONS:"]
        
        # Explain and Educate
        sections.append("- EXPLAIN METRICS: Whenever you mention Beta, Sharpe Ratio, VaR, Expected Shortfall, HHI, Effective Holdings, Maximum Drawdown, Tracking Error, Information Ratio, Alpha, Diversification Score, or Portfolio Health, you MUST explain what it measures, why it matters, and what this portfolio's specific value indicates.")
        sections.append("- CONFLICT RESOLUTION: If two metrics appear contradictory (e.g., beta is low but volatility is high, or risk is moderate but health is poor), explain WHY rather than ignoring the conflict. Synthesize the reality.")
        sections.append("- Identify the three biggest strengths and three biggest risks based on data.")
        sections.append("- Prioritize the most important actionable recommendations.")
        sections.append("- Base every statement ONLY on the supplied analytics. Never invent facts or financial metrics.")
        sections.append("- Never contradict supplied analytics.")
        sections.append("- Never provide personalized financial advice (use educational tones).")
        
        # Structural Enforcement
        sections.append("- OUTPUT FORMAT: Return valid JSON ONLY. The JSON must strictly contain the following keys:")
        sections.append('  { "Executive Summary": "...", "Portfolio Story": "...", "Key Findings": "...", "Risk Commentary": "...", "Performance Commentary": "...", "Benchmark Commentary": "...", "Diversification Commentary": "...", "Priority Actions": "...", "Future Outlook": "...", "Investor Profile": "...", "Holding Insights": "...", "Sector Insights": "..." }')
        
        return sections

    def _join_items(self, values: Any) -> str:
        if not values:
            return "N/A"
        if isinstance(values, str):
            return values
        if isinstance(values, dict):
            return self._string_or_default(values.get("title") or values.get("summary") or values.get("description"), "N/A")
        items = []
        for value in values[:3]:
            if isinstance(value, dict):
                item_text = value.get("title") or value.get("summary") or value.get("description") or value.get("name")
            else:
                item_text = value
            if item_text:
                items.append(str(item_text))
        return "; ".join(items) if items else "N/A"

    def _join_mapping(self, values: Dict[str, Any]) -> str:
        if not values:
            return "N/A"
        return ", ".join(f"{key}: {self._format_ratio(value)}" for key, value in values.items())

    def _format_dimension_rank(self, breakdown: Dict[str, Any], descending: bool) -> str:
        if not breakdown:
            return "N/A"
        ordered = sorted(breakdown.items(), key=lambda item: self._coerce_float(item[1]) or 0.0, reverse=descending)
        return ", ".join(name for name, _ in ordered[:3]) if ordered else "N/A"

    def _format_number(self, value: Any) -> str:
        if value is None:
            return "N/A"
        numeric = self._coerce_float(value)
        if numeric is None:
            return str(value)
        return str(int(numeric)) if abs(numeric - round(numeric)) < 1e-9 else f"{round(numeric, 2):.2f}"

    def _format_value(self, value: Any, kind: str = "text") -> str:
        if value is None:
            return "N/A"
        if kind == "currency":
            return self._format_currency(value)
        if kind == "percent":
            return self._format_percent(value)
        if kind == "ratio":
            return self._format_ratio(value)
        return str(value)

    def _format_currency(self, value: Any) -> str:
        if value is None:
            return "N/A"
        numeric = self._coerce_float(value)
        if numeric is None:
            return str(value)
        rounded = round(numeric, 2)
        if abs(rounded - round(rounded)) < 1e-9:
            return f"₹{int(round(rounded)):,}"
        return f"₹{rounded:,.2f}"

    def _format_percent(self, value: Any) -> str:
        if value is None:
            return "N/A"
        numeric = self._coerce_float(value)
        if numeric is None:
            return str(value)
        return f"{round(numeric, 2):.2f}%"

    def _format_ratio(self, value: Any) -> str:
        if value is None:
            return "N/A"
        numeric = self._coerce_float(value)
        if numeric is None:
            return str(value)
        return f"{round(numeric, 2):.2f}"

    def _string_or_default(self, value: Any, default: str = "N/A") -> str:
        if value is None:
            return default
        return str(value)

    def _nested_nested_value(self, container: Optional[Dict[str, Any]], key: str, nested_key: str) -> Any:
        if isinstance(container, dict):
            nested = container.get(key)
            if isinstance(nested, dict):
                return nested.get(nested_key)
        return None

    def _coerce_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(str(value))
        except (TypeError, ValueError):
            return None