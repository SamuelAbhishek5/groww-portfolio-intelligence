from typing import Any, Dict, List


class InsightFormatter:
    """Normalize validated insight payloads into a stable schema for downstream consumers."""

    def format(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = payload or {}
        return {
            "executive_summary": self._string(payload.get("executive_summary"), ""),
            "portfolio_story": self._string(payload.get("portfolio_story"), ""),
            "strengths": self._string_list(payload.get("strengths")),
            "weaknesses": self._string_list(payload.get("weaknesses")),
            "risk_commentary": self._string(payload.get("risk_commentary"), ""),
            "performance_commentary": self._string(payload.get("performance_commentary"), ""),
            "benchmark_commentary": self._string(payload.get("benchmark_commentary"), ""),
            "diversification_commentary": self._string(payload.get("diversification_commentary"), ""),
            "holding_insights": self._normalize_holding_insights(payload.get("holding_insights")),
            "sector_insights": self._normalize_sector_insights(payload.get("sector_insights")),
            "priority_actions": self._normalize_priority_actions(payload.get("priority_actions")),
            "future_outlook": self._string(payload.get("future_outlook"), ""),
            "investor_profile": self._normalize_profile(payload.get("investor_profile")),
        }

    def _normalize_profile(self, profile: Any) -> Dict[str, Any]:
        if not isinstance(profile, dict):
            return {"type": "Unknown", "confidence": 0.0, "reason": "Insufficient analytics supplied."}
        return {
            "type": self._string(profile.get("type"), "Unknown"),
            "confidence": self._float(profile.get("confidence"), 0.0),
            "reason": self._string(profile.get("reason"), "Insufficient analytics supplied."),
        }

    def _normalize_holding_insights(self, items: Any) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for item in items[:8]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "symbol": self._string(item.get("symbol"), ""),
                    "company": self._string(item.get("company"), ""),
                    "analysis": self._string(item.get("analysis"), ""),
                    "strengths": self._string_list(item.get("strengths")),
                    "risks": self._string_list(item.get("risks")),
                    "recommendation": self._string(item.get("recommendation"), "Monitor"),
                }
            )
        return normalized

    def _normalize_sector_insights(self, items: Any) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for item in items[:8]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "sector": self._string(item.get("sector"), ""),
                    "analysis": self._string(item.get("analysis"), ""),
                    "recommendation": self._string(item.get("recommendation"), "Monitor"),
                }
            )
        return normalized

    def _normalize_priority_actions(self, items: Any) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for item in items[:5]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "priority": self._string(item.get("priority"), "Medium"),
                    "title": self._string(item.get("title"), "Review allocation"),
                    "reason": self._string(item.get("reason"), "Review the supplied analytics."),
                }
            )
        return normalized

    def _string(self, value: Any, fallback: str) -> str:
        if isinstance(value, str):
            return value.strip() or fallback
        if value is None:
            return fallback
        return str(value).strip() or fallback

    def _string_list(self, values: Any) -> List[str]:
        if not isinstance(values, list):
            return []
        return [self._string(item, "") for item in values if self._string(item, "")]

    def _float(self, value: Any, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback
