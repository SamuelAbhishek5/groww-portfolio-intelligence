import json
import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class ResponseParser:
    """Validate and normalize AI JSON responses into the expected schema."""

    REQUIRED_FIELDS = {
        "executive_summary": str,
        "portfolio_story": str,
        "strengths": list,
        "weaknesses": list,
        "risk_commentary": str,
        "performance_commentary": str,
        "benchmark_commentary": str,
        "diversification_commentary": str,
        "future_outlook": str,
        "investor_profile": dict,
    }
    OPTIONAL_FIELDS = {
        "holding_insights": list,
        "sector_insights": list,
        "priority_actions": list,
    }

    def parse_and_validate(self, payload: str) -> Tuple[Dict[str, Any], List[str]]:
        errors: List[str] = []
        if not payload or not payload.strip():
            return self._fallback_payload(), ["Empty response from LLM."]

        parsed = self._extract_json_object(payload)
        if parsed is None:
            logger.warning("LLM response was not valid JSON")
            return self._fallback_payload(), ["Malformed JSON response from LLM."]
        if not isinstance(parsed, dict):
            logger.warning("LLM response root object was not a JSON object")
            return self._fallback_payload(), ["LLM response root must be an object."]

        normalized = self._normalize(parsed, errors)
        return normalized, errors

    def _extract_json_object(self, payload: str) -> Any:
        cleaned = payload.strip()
        if not cleaned:
            return None
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            start = cleaned.find("{")
            if start < 0:
                return None
            try:
                return decoder.raw_decode(cleaned[start:])[0]
            except json.JSONDecodeError:
                return None

    def _normalize(self, payload: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        normalized = self._fallback_payload()

        for field_name in self.REQUIRED_FIELDS:
            value = payload.get(field_name)
            if field_name in payload and value is not None:
                normalized[field_name] = self._coerce_value(field_name, value)
            else:
                errors.append(f"Missing required field: {field_name}")

        for field_name in self.OPTIONAL_FIELDS:
            if field_name in payload and payload[field_name] is not None:
                normalized[field_name] = self._coerce_value(field_name, payload[field_name])

        investor_profile = payload.get("investor_profile")
        if isinstance(investor_profile, dict):
            normalized["investor_profile"] = {
                "type": self._coerce_string(investor_profile.get("type"), "Balanced"),
                "confidence": self._clamp_float(self._coerce_float(investor_profile.get("confidence"), 0.5), 0.0, 1.0),
                "reason": self._coerce_string(investor_profile.get("reason"), "Based on supplied analytics."),
            }
        else:
            errors.append("investor_profile must be an object")

        normalized["strengths"] = self._normalize_string_list(payload.get("strengths"))
        normalized["weaknesses"] = self._normalize_string_list(payload.get("weaknesses"))
        normalized["holding_insights"] = self._normalize_holding_insights(payload.get("holding_insights"))
        normalized["sector_insights"] = self._normalize_sector_insights(payload.get("sector_insights"))
        normalized["priority_actions"] = self._normalize_priority_actions(payload.get("priority_actions"))

        return normalized

    def _coerce_value(self, field_name: str, value: Any) -> Any:
        if field_name in {"executive_summary", "portfolio_story", "risk_commentary", "performance_commentary", "benchmark_commentary", "diversification_commentary", "future_outlook"}:
            return self._coerce_string(value, "")
        if field_name in {"strengths", "weaknesses"}:
            return self._normalize_string_list(value)
        if field_name == "investor_profile":
            return value if isinstance(value, dict) else {}
        if field_name in {"holding_insights", "sector_insights", "priority_actions"}:
            return value if isinstance(value, list) else []
        return value

    def _normalize_holding_insights(self, value: Any) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for item in value[:8]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "symbol": self._coerce_string(item.get("symbol"), ""),
                    "company": self._coerce_string(item.get("company"), ""),
                    "analysis": self._coerce_string(item.get("analysis"), ""),
                    "strengths": self._normalize_string_list(item.get("strengths")),
                    "risks": self._normalize_string_list(item.get("risks")),
                    "recommendation": self._coerce_string(item.get("recommendation"), "Monitor"),
                }
            )
        return normalized

    def _normalize_sector_insights(self, value: Any) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for item in value[:8]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "sector": self._coerce_string(item.get("sector"), ""),
                    "analysis": self._coerce_string(item.get("analysis"), ""),
                    "recommendation": self._coerce_string(item.get("recommendation"), "Monitor"),
                }
            )
        return normalized

    def _normalize_priority_actions(self, value: Any) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for item in value[:5]:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "priority": self._normalize_priority(item.get("priority")),
                    "title": self._coerce_string(item.get("title"), "Review allocation"),
                    "reason": self._coerce_string(item.get("reason"), "Review the supplied analytics."),
                }
            )
        return normalized

    def _normalize_string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [self._coerce_string(item, "") for item in value if self._coerce_string(item, "")]

    def _normalize_priority(self, value: Any) -> str:
        priority = self._coerce_string(value, "Medium").lower()
        if priority in {"critical", "high", "medium", "low"}:
            return priority.capitalize()
        return "Medium"

    def _coerce_string(self, value: Any, fallback: str) -> str:
        if isinstance(value, str):
            return value.strip() or fallback
        if value is None:
            return fallback
        return str(value).strip() or fallback

    def _coerce_float(self, value: Any, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _clamp_float(self, value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))

    def _fallback_payload(self) -> Dict[str, Any]:
        return {
            "executive_summary": "The portfolio analysis is currently unavailable. Please review the deterministic analytics output.",
            "portfolio_story": "Portfolio insights could not be generated from the supplied data.",
            "strengths": [],
            "weaknesses": [],
            "risk_commentary": "Risk commentary is unavailable because the required analytics were not supplied.",
            "performance_commentary": "Performance commentary is unavailable because the required analytics were not supplied.",
            "benchmark_commentary": "Benchmark commentary is unavailable because the required analytics were not supplied.",
            "diversification_commentary": "Diversification commentary is unavailable because the required analytics were not supplied.",
            "holding_insights": [],
            "sector_insights": [],
            "priority_actions": [],
            "future_outlook": "Outlook is unavailable until the deterministic analytics are reviewed.",
            "investor_profile": {"type": "Unknown", "confidence": 0.0, "reason": "Insufficient analytics supplied."},
        }
