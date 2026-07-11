from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HoldingInsight:
    symbol: str = ""
    company: str = ""
    analysis: str = ""
    strengths: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "company": self.company,
            "analysis": self.analysis,
            "strengths": self.strengths,
            "risks": self.risks,
            "recommendation": self.recommendation,
        }


@dataclass
class SectorInsight:
    sector: str = ""
    analysis: str = ""
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"sector": self.sector, "analysis": self.analysis, "recommendation": self.recommendation}


@dataclass
class PriorityAction:
    priority: str = "Medium"
    title: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"priority": self.priority, "title": self.title, "reason": self.reason}


@dataclass
class InvestorProfile:
    type: str = "Unknown"
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "confidence": self.confidence, "reason": self.reason}


@dataclass
class InsightPayload:
    executive_summary: str = ""
    portfolio_story: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    risk_commentary: str = ""
    performance_commentary: str = ""
    benchmark_commentary: str = ""
    diversification_commentary: str = ""
    holding_insights: List[HoldingInsight] = field(default_factory=list)
    sector_insights: List[SectorInsight] = field(default_factory=list)
    priority_actions: List[PriorityAction] = field(default_factory=list)
    future_outlook: str = ""
    investor_profile: Optional[InvestorProfile] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executive_summary": self.executive_summary,
            "portfolio_story": self.portfolio_story,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "risk_commentary": self.risk_commentary,
            "performance_commentary": self.performance_commentary,
            "benchmark_commentary": self.benchmark_commentary,
            "diversification_commentary": self.diversification_commentary,
            "holding_insights": [item.to_dict() for item in self.holding_insights],
            "sector_insights": [item.to_dict() for item in self.sector_insights],
            "priority_actions": [item.to_dict() for item in self.priority_actions],
            "future_outlook": self.future_outlook,
            "investor_profile": (self.investor_profile or InvestorProfile()).to_dict(),
        }
