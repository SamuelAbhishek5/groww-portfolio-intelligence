import json
import logging
from typing import Any, Dict, List, Optional

from backend.ai.insight_formatter import InsightFormatter
from backend.ai.llm_client import BaseLLMClient, GeminiLLMClient
from backend.ai.prompt_builder import PromptBuilder
from backend.ai.response_parser import ResponseParser

logger = logging.getLogger(__name__)


class AIInsightEngine:
    """Translate deterministic portfolio analytics into schema-aligned AI insights."""

    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        response_parser: Optional[ResponseParser] = None,
        formatter: Optional[InsightFormatter] = None,
    ) -> None:
        self.llm_client = llm_client or GeminiLLMClient()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.response_parser = response_parser or ResponseParser()
        self.formatter = formatter or InsightFormatter()

    def generate_insights(
        self,
        portfolio_json: Optional[Dict[str, Any]] = None,
        risk_metrics: Optional[Dict[str, Any]] = None,
        health_metrics: Optional[Dict[str, Any]] = None,
        benchmark_metrics: Optional[Dict[str, Any]] = None,
        opportunity_result: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = 30,
    ) -> Dict[str, Any]:
        """Generate structured portfolio insights from deterministic analytics outputs."""
        try:
            prompt = self.prompt_builder.build_prompt(
                portfolio_json=portfolio_json,
                risk_metrics=risk_metrics,
                health_metrics=health_metrics,
                benchmark_metrics=benchmark_metrics,
                opportunity_result=opportunity_result,
            )
            system_prompt = self.prompt_builder.build_system_prompt()

            raw_response = self._generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                timeout=timeout,
                portfolio_json=portfolio_json,
                risk_metrics=risk_metrics,
                health_metrics=health_metrics,
                benchmark_metrics=benchmark_metrics,
                opportunity_result=opportunity_result,
            )
            
            parsed_payload, errors = self.response_parser.parse_and_validate(raw_response)
            if errors:
                logger.warning("Insight parsing produced warnings: %s", errors)
            return self.formatter.format(parsed_payload)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("AI insight generation failed: %s", exc)
            return self._build_fallback_payload(
                portfolio_json=portfolio_json,
                risk_metrics=risk_metrics,
                health_metrics=health_metrics,
                benchmark_metrics=benchmark_metrics,
                opportunity_result=opportunity_result,
            )

    def _generate_with_fallback(
        self,
        prompt: str,
        system_prompt: str,
        timeout: Optional[int],
        portfolio_json: Optional[Dict[str, Any]] = None,
        risk_metrics: Optional[Dict[str, Any]] = None,
        health_metrics: Optional[Dict[str, Any]] = None,
        benchmark_metrics: Optional[Dict[str, Any]] = None,
        opportunity_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        try:
            return self.llm_client.generate(prompt, system_prompt=system_prompt, timeout=timeout)
        except Exception as exc:
            logger.warning("LLM generation failed, using analytics-driven fallback: %s", exc)
            return self._build_fallback_response(
                portfolio_json=portfolio_json,
                risk_metrics=risk_metrics,
                health_metrics=health_metrics,
                benchmark_metrics=benchmark_metrics,
                opportunity_result=opportunity_result,
            )

    def _build_fallback_response(
        self,
        portfolio_json: Optional[Dict[str, Any]] = None,
        risk_metrics: Optional[Dict[str, Any]] = None,
        health_metrics: Optional[Dict[str, Any]] = None,
        benchmark_metrics: Optional[Dict[str, Any]] = None,
        opportunity_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        payload = self._build_fallback_payload(
            portfolio_json=portfolio_json,
            risk_metrics=risk_metrics,
            health_metrics=health_metrics,
            benchmark_metrics=benchmark_metrics,
            opportunity_result=opportunity_result,
        )
        return json.dumps(payload)

    def _build_fallback_payload(
        self,
        portfolio_json: Optional[Dict[str, Any]] = None,
        risk_metrics: Optional[Dict[str, Any]] = None,
        health_metrics: Optional[Dict[str, Any]] = None,
        benchmark_metrics: Optional[Dict[str, Any]] = None,
        opportunity_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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
        holding_summary = risk_metrics.get("holding_summary", {}) or {}
        portfolio_health = health_metrics.get("portfolio_health", {}) or {}
        opportunity_summary = self._coerce_opportunity_summary(opportunity_result.get("summary"))
        action_plan = opportunity_result.get("action_plan", []) or []

        invested_value = self._coerce_float(portfolio_summary.get("total_invested_value"))
        live_value = self._coerce_float(portfolio_summary.get("total_live_value"))
        return_pct = self._portfolio_return_pct(invested_value, live_value)
        beta = self._coerce_float(risk_summary.get("portfolio_beta"))
        if beta is None:
            beta = self._coerce_float(risk_metrics.get("summary", {}).get("portfolio_beta"))
        risk_score = self._coerce_float(risk_summary.get("risk_score"))
        if risk_score is None:
            risk_score = self._coerce_float(risk_metrics.get("risk_score"))
        top_weight_pct = self._coerce_float(concentration_risk.get("top_holding_weight_pct"))
        if top_weight_pct is None:
            top_weight_pct = self._coerce_float(concentration_risk.get("top_holding_weight"))
        max_drawdown_pct = self._coerce_float(self._nested_value(risk_summary, "max_drawdown", "percent"))
        if max_drawdown_pct is None:
            max_drawdown_pct = self._coerce_float(risk_metrics.get("summary", {}).get("max_drawdown"))
        benchmark_relative_performance = self._coerce_float(benchmark_metrics.get("portfolio_relative_performance_pct"))
        benchmark_return_pct = self._coerce_float(benchmark_metrics.get("benchmark_return_pct"))
        portfolio_return_pct = self._coerce_float(benchmark_metrics.get("portfolio_return_pct"))
        if portfolio_return_pct is None:
            portfolio_return_pct = self._coerce_float(benchmark_metrics.get("portfolio_weighted_return_pct"))
        diversification_score = self._coerce_float(diversification.get("score"))
        average_correlation = self._coerce_float(correlation.get("average"))
        health_grade = portfolio_health.get("grade") or ""
        strongest_stock = benchmark_metrics.get("strongest_stock") or ""
        weakest_stock = benchmark_metrics.get("weakest_stock") or ""
        largest_risk_contributor = holding_summary.get("largest_risk_contributor") or holding_summary.get("highest_risk_stock") or ""

        executive_summary_parts: List[str] = []
        if benchmark_relative_performance is not None and benchmark_relative_performance < 0:
            executive_summary_parts.append(
                f"The portfolio underperformed the benchmark by {abs(benchmark_relative_performance):.2f}% in the supplied analytics."
            )
        if top_weight_pct is not None and top_weight_pct >= 45.0:
            executive_summary_parts.append(
                f"Concentration is elevated because the largest holding represents {top_weight_pct:.2f}% of portfolio value."
            )
        if beta is not None and beta < 1.0:
            executive_summary_parts.append(f"Portfolio beta is {beta:.2f}, below market sensitivity.")
        if max_drawdown_pct is not None and max_drawdown_pct >= 25.0:
            executive_summary_parts.append(f"Maximum drawdown reached {max_drawdown_pct:.2f}%.")
        if largest_risk_contributor:
            executive_summary_parts.append(f"{largest_risk_contributor} is the largest contributor to portfolio risk.")
        if not executive_summary_parts:
            executive_summary_parts.append("The supplied analytics support a measured review of concentration, risk, and benchmark-relative performance.")
        executive_summary = " ".join(executive_summary_parts)

        strengths: List[str] = []
        if health_grade:
            strengths.append(f"Portfolio health is rated {health_grade}.")
        if diversification_score is not None:
            strengths.append(f"Diversification score is {diversification_score:.2f}.")
        if beta is not None and beta < 1.0:
            strengths.append(f"Beta is {beta:.2f}, which is below the market benchmark.")
        if strongest_stock:
            strengths.append(f"{strongest_stock} is the strongest benchmark-relative holding.")
        if not strengths and isinstance(opportunity_summary, dict) and opportunity_summary.get("key_strength"):
            strengths.append(str(opportunity_summary["key_strength"]))

        weaknesses: List[str] = []
        if top_weight_pct is not None and top_weight_pct >= 45.0:
            weaknesses.append(f"The largest holding accounts for {top_weight_pct:.2f}% of portfolio value.")
        if benchmark_relative_performance is not None and benchmark_relative_performance < 0:
            weaknesses.append(f"Relative performance trailed the benchmark by {abs(benchmark_relative_performance):.2f}%.")
        if max_drawdown_pct is not None and max_drawdown_pct >= 25.0:
            weaknesses.append(f"Maximum drawdown reached {max_drawdown_pct:.2f}%.")
        if risk_score is not None and risk_score >= 70.0:
            weaknesses.append(f"Risk score is {risk_score:.2f}, indicating elevated caution.")
        if not weaknesses and isinstance(opportunity_summary, dict) and opportunity_summary.get("highest_priority_issue"):
            weaknesses.append(str(opportunity_summary["highest_priority_issue"]))

        risk_commentary = "Risk commentary is based on the supplied risk metrics."
        if risk_score is not None and beta is not None:
            risk_commentary = f"Risk is {risk_summary.get('risk_level', 'Unknown')} with a risk score of {risk_score:.2f} and a portfolio beta of {beta:.2f}."
        if max_drawdown_pct is not None:
            risk_commentary += f" Maximum drawdown is {max_drawdown_pct:.2f}%."
        if top_weight_pct is not None:
            risk_commentary += f" The largest holding accounts for {top_weight_pct:.2f}% of the portfolio."

        performance_commentary = "Performance commentary is based on the supplied benchmark and portfolio return metrics."
        if portfolio_return_pct is not None and benchmark_return_pct is not None:
            performance_commentary = f"The portfolio returned {portfolio_return_pct:.2f}% versus {benchmark_return_pct:.2f}% for the benchmark."
        if benchmark_relative_performance is not None:
            performance_commentary += f" Relative performance was {benchmark_relative_performance:.2f}%."

        benchmark_commentary = "Benchmark commentary is based on the supplied benchmark metrics."
        if benchmark_metrics.get("benchmark_name"):
            benchmark_commentary = f"Benchmark commentary refers to {benchmark_metrics['benchmark_name']} and the reported relative performance."
        if strongest_stock or weakest_stock:
            benchmark_commentary += f" The strongest holding is {strongest_stock or 'N/A'} and the weakest is {weakest_stock or 'N/A'}."

        diversification_commentary = "Diversification commentary is based on the supplied concentration and correlation analytics."
        if diversification_score is not None:
            diversification_commentary = f"Diversification score is {diversification_score:.2f} with an average correlation of {average_correlation:.2f}."
        if concentration_risk.get("top_sector"):
            diversification_commentary += f" The largest sector is {concentration_risk['top_sector']}."

        holding_insights = self._build_holding_insights(holding_analysis)
        sector_insights = self._build_sector_insights(holdings)
        priority_actions = self._build_priority_actions(action_plan, benchmark_relative_performance, top_weight_pct, stress_test)
        future_outlook = self._future_outlook(portfolio_health, benchmark_relative_performance, top_weight_pct)
        investor_profile = self._build_investor_profile(risk_score, beta, top_weight_pct)

        story_text = ""
        if isinstance(opportunity_summary, dict):
            story_text = self._string(opportunity_summary.get("top_recommendation") or opportunity_summary.get("highest_priority_issue"))
        if not story_text and isinstance(opportunity_result, dict):
            story_text = self._string(opportunity_result.get("summary"))

        payload = {
            "executive_summary": executive_summary,
            "portfolio_story": story_text or "The portfolio story is grounded in the supplied analytics and should be interpreted alongside the underlying metrics.",
            "strengths": strengths or ["The supplied analytics describe a clearly defined portfolio structure."],
            "weaknesses": weaknesses or ["The portfolio would benefit from closer review of concentration and performance outcomes."],
            "risk_commentary": risk_commentary,
            "performance_commentary": performance_commentary,
            "benchmark_commentary": benchmark_commentary,
            "diversification_commentary": diversification_commentary,
            "holding_insights": holding_insights,
            "sector_insights": sector_insights,
            "priority_actions": priority_actions,
            "future_outlook": future_outlook,
            "investor_profile": investor_profile,
        }
        return self.formatter.format(payload)

    def _build_holding_insights(self, holding_analysis: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        insights: List[Dict[str, Any]] = []
        for item in holding_analysis[:5]:
            if not isinstance(item, dict):
                continue
            symbol = self._string(item.get("symbol"))
            company = self._string(item.get("company")) or self._string(item.get("company_name")) or symbol
            weight_pct = self._coerce_float(item.get("weight_pct"))
            risk_level = self._string(item.get("risk_level"))
            risk_score = self._coerce_float(item.get("risk_score"))
            risk_contribution_pct = self._coerce_float(item.get("risk_contribution_pct"))
            strengths: List[str] = []
            risks: List[str] = []
            if weight_pct is not None:
                strengths.append(f"Represents {weight_pct:.2f}% of portfolio value.")
            if risk_level:
                strengths.append(f"Current risk profile is {risk_level}.")
            if risk_contribution_pct is not None and risk_contribution_pct >= 50.0:
                risks.append(f"Largest contributor to risk at {risk_contribution_pct:.2f}%.")
            if risk_score is not None and risk_score >= 45.0:
                risks.append(f"Risk score is {risk_score:.0f}.")
            insights.append(
                {
                    "symbol": symbol,
                    "company": company,
                    "analysis": f"{company} is included in the current allocation and should be reviewed alongside the portfolio's concentration profile." if company else "Holding is present in the supplied analytics.",
                    "strengths": strengths or ["Included in the supplied holdings data."],
                    "risks": risks or ["Monitor this holding in the broader portfolio context."],
                    "recommendation": "Monitor the position as part of the portfolio's concentration and risk review." if risks else "Maintain current monitoring until new analytics are available.",
                }
            )
        return insights

    def _build_sector_insights(self, holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sector_weights: Dict[str, float] = {}
        for holding in holdings:
            if not isinstance(holding, dict):
                continue
            sector = self._string(holding.get("sector"))
            if not sector:
                continue
            live_value = self._coerce_float(holding.get("live_value")) or 0.0
            sector_weights[sector] = sector_weights.get(sector, 0.0) + live_value
        insights: List[Dict[str, Any]] = []
        for sector, value in sorted(sector_weights.items(), key=lambda item: item[1], reverse=True)[:5]:
            insights.append(
                {
                    "sector": sector,
                    "analysis": f"Sector exposure totals {value:,.2f} in current portfolio value.",
                    "recommendation": "Review this sector in the context of diversification targets." if value else "Monitor sector exposure.",
                }
            )
        return insights

    def _build_priority_actions(
        self,
        action_plan: List[Dict[str, Any]],
        benchmark_relative_performance: Optional[float],
        top_weight_pct: Optional[float],
        stress_test: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if action_plan:
            return [
                {
                    "priority": self._string(item.get("priority")) or "Medium",
                    "title": self._string(item.get("title")) or "Review allocation",
                    "reason": self._string(item.get("action")) or self._string(item.get("reason")) or "Review the supplied analytics.",
                }
                for item in action_plan[:5]
                if isinstance(item, dict)
            ]

        actions: List[Dict[str, Any]] = []
        if top_weight_pct is not None and top_weight_pct >= 45.0:
            actions.append({"priority": "High", "title": "Review concentration", "reason": "The largest holding remains a dominant share of portfolio value."})
        if benchmark_relative_performance is not None and benchmark_relative_performance < 0.0:
            actions.append({"priority": "Medium", "title": "Review benchmark-relative performance", "reason": "The portfolio underperformed the benchmark in the supplied analytics."})
        if isinstance(stress_test, dict) and stress_test:
            actions.append({"priority": "Medium", "title": "Review downside sensitivity", "reason": "Stress test scenarios indicate material downside sensitivity."})
        if not actions:
            actions.append({"priority": "Low", "title": "Revisit portfolio positioning", "reason": "The current analytics support a periodic allocation review."})
        return actions

    def _future_outlook(self, portfolio_health: Dict[str, Any], benchmark_relative_performance: Optional[float], top_weight_pct: Optional[float]) -> str:
        health_status = self._string(portfolio_health.get("status"))
        outlook_parts = []
        if health_status:
            outlook_parts.append(f"Portfolio health is currently {health_status.lower()}.")
        if benchmark_relative_performance is not None and benchmark_relative_performance < 0.0:
            outlook_parts.append("Near-term performance will depend on improving benchmark-relative results.")
        if top_weight_pct is not None and top_weight_pct >= 45.0:
            outlook_parts.append("Concentration reduction remains an important lever for resilience.")
        if not outlook_parts:
            outlook_parts.append("The outlook is shaped by the supplied risk, health, and benchmark analytics.")
        return " ".join(outlook_parts)

    def _build_investor_profile(self, risk_score: Optional[float], beta: Optional[float], top_weight_pct: Optional[float]) -> Dict[str, Any]:
        if risk_score is not None and risk_score >= 70.0:
            return {"type": "Defensive", "confidence": 0.8, "reason": "The supplied risk score and concentration metrics suggest a more cautious stance."}
        if beta is not None and beta < 1.0:
            return {"type": "Balanced", "confidence": 0.7, "reason": "The analytics indicate lower-than-market sensitivity with moderate concentration."}
        if top_weight_pct is not None and top_weight_pct >= 45.0:
            return {"type": "Balanced", "confidence": 0.65, "reason": "The portfolio is concentrated, but the supplied risk profile remains manageable."}
        return {"type": "Growth", "confidence": 0.6, "reason": "The supplied analytics suggest a moderate growth-oriented profile with room for diversification."}

    def _portfolio_return_pct(self, invested_value: Optional[float], live_value: Optional[float]) -> Optional[float]:
        if invested_value is None or live_value is None or invested_value == 0:
            return None
        return ((live_value - invested_value) / invested_value) * 100.0

    def _coerce_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _coerce_opportunity_summary(self, summary: Any) -> Any:
        if isinstance(summary, dict):
            return summary
        if isinstance(summary, str):
            return {"summary": summary}
        return {}

    def _nested_value(self, container: Optional[Dict[str, Any]], key: str, nested_key: str) -> Any:
        if not isinstance(container, dict):
            return None
        nested = container.get(key)
        if isinstance(nested, dict):
            return nested.get(nested_key)
        return None

    def _string(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()
