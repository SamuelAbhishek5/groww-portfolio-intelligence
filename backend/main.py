from backend.services.portfolio_enrichment import PortfolioEnricher
from backend.analytics.portfolio_reporter import PortfolioReporter
from backend.analytics.risk_engine import RiskEngine
from backend.analytics.benchmark_engine import BenchmarkEngine
from backend.analytics.opportunity_engine import OpportunityEngine
from backend.analytics.portfolio_health import PortfolioHealthEngine
from backend.ai.ai_insight_engine import AIInsightEngine
from backend.ai.chatbot import PortfolioChatbot
import json

def main():
    enricher = PortfolioEnricher()
    risk_engine = RiskEngine()
    benchmark_engine = BenchmarkEngine()
    opportunity_engine = OpportunityEngine()
    health_engine = PortfolioHealthEngine()
    insight_engine = AIInsightEngine()
    chat_engine = PortfolioChatbot()

    file_path = "Stocks_Holdings_Statement_4214763833_2026-06-19.xlsx"

    try:
        portfolio_json = enricher.process_portfolio(
            source_type="excel",
            source_data=file_path,
        )

        #print("Portfolio JSON:")
        #print(json.dumps(portfolio_json, indent=2, default=str))

        risk_metrics = risk_engine.evaluate_portfolio(portfolio_json)
        benchmark_metrics = benchmark_engine.compare_portfolio(portfolio_json)
        reporter = PortfolioReporter(portfolio_json)

        print("\nRisk Metrics:")
        print(json.dumps(risk_metrics, indent=2, default=str))
        #print("\nBenchmark Metrics:")
        #print(json.dumps(benchmark_metrics, indent=2, default=str))
        #reporter.print_dashboard_metrics()

        health_metrics = health_engine.calculate_health(portfolio_json, benchmark_metrics=benchmark_metrics)
        #print("\nPortfolio Health Metrics:")
        #print(json.dumps(health_metrics, indent=2, default=str))

        opportunity_result = opportunity_engine.analyze(
            portfolio_json=portfolio_json,
            risk_metrics=risk_metrics,
            benchmark_metrics=benchmark_metrics,
            health_metrics=health_metrics,
        )

        #insight_result = insight_engine.generate_insights(
        #    portfolio_json=portfolio_json,
        #    risk_metrics=risk_metrics,
        #    health_metrics=health_metrics,
       #    benchmark_metrics=benchmark_metrics,
        #    opportunity_result=opportunity_result,
        #)
        user_message = "What are the key risks in my portfolio?"
        #user_message = "Which holding is riskiest?"
        #chat_response = chat_engine.chat(
        #    user_query=user_message,
         #   risk_metrics=risk_metrics,
        #    health_metrics=health_metrics,
        #    benchmark_metrics=benchmark_metrics,
        #    opportunity_result=opportunity_result
        #)
       # print("\n========== AI CHATBOT RESPONSE ==========")
        #print(json.dumps(chat_response, indent=2, default=str))
        #print("\nOpportunity Engine result:\n")
        #print(json.dumps(opportunity_result, indent=2, default=str))
        #print("\n========== OPPORTUNITY REPORT ==========")
        #print(opportunity_result["summary"])

        #print("\nStrengths")
        #for item in opportunity_result.get("strengths", []):
            #print("-", item["title"])

        #print("\nRisks")
        #for item in opportunity_result.get("risks", []):
            #print("-", item["title"])

        #print("\nOpportunities")
        #for item in opportunity_result.get("opportunities", []):
            #print("-", item["title"])

        #print("\nAction Plan")
        #for item in opportunity_result.get("action_plan", []):
            #print("-", item["title"])

        #print("\n========== AI INSIGHT REPORT ==========")
        #print(json.dumps(insight_result, indent=2, default=str))
    except Exception as exc:
        print(f"Risk engine execution failed: {exc}")


if __name__ == "__main__":
    main()
