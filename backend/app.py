import json
from pathlib import Path
from uuid import uuid4
import re
#from sympy import re

from backend.services.portfolio_enrichment import PortfolioEnricher
from backend.analytics.portfolio_reporter import PortfolioReporter
from backend.analytics.risk_engine import RiskEngine
from backend.analytics.benchmark_engine import BenchmarkEngine
from backend.analytics.opportunity_engine import OpportunityEngine
from backend.analytics.portfolio_health import PortfolioHealthEngine
from backend.ai.ai_insight_engine import AIInsightEngine
from backend.ai.chatbot import PortfolioChatbot

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.pdf.report_generator import create_portfolio_pdf

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
UPLOAD_DIR = BASE_DIR / 'uploads'
REPORT_DIR = BASE_DIR / 'reports'
STATE_DIR = BASE_DIR / 'state'

for directory in (UPLOAD_DIR, REPORT_DIR, STATE_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title='Groww Portfolio Intelligence API')
app.mount('/reports', StaticFiles(directory=REPORT_DIR), name='reports')

STATUS_FILE = 'status.json'


def _state_path(report_id: str) -> Path:
    return STATE_DIR / f'{report_id}.json'


def _write_state(report_id: str, payload: dict) -> None:
    state_file = _state_path(report_id)
    state_file.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def _read_state(report_id: str) -> dict:
    state_file = _state_path(report_id)
    if not state_file.exists():
        raise FileNotFoundError
    return json.loads(state_file.read_text(encoding='utf-8'))


def _safe_url(report_id: str) -> str:
    return f'/reports/{report_id}.pdf'


def _coerce_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_currency(value) -> str:
    numeric_value = _coerce_float(value)
    if numeric_value is None:
        return '-'
    return f'₹ {numeric_value:,.0f}'


def _format_percent(value) -> str:
    numeric_value = _coerce_float(value)
    if numeric_value is None:
        return '-'
    return f'{numeric_value:.1f}%'


def _derive_sectors(portfolio_json: dict) -> str:
    holdings = portfolio_json.get('holdings', []) or []
    sectors = [holding.get('sector') for holding in holdings if holding.get('sector')]
    if not sectors:
        return '-'
    return ', '.join(dict.fromkeys(sectors))


@app.get("/")
async def home():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.post('/api/upload')
async def upload_report(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail='Missing uploaded file.')

    report_id = uuid4().hex
    suffix = Path(file.filename).suffix or '.xlsx'
    upload_path = UPLOAD_DIR / f'{report_id}{suffix}'

    try:
        contents = await file.read()
        upload_path.write_bytes(contents)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Unable to save file: {exc}')

    report_path = REPORT_DIR / f'{report_id}.pdf'
    state_payload = {
        'report_id': report_id,
        'status': 'processing',
        'pdf_url': _safe_url(report_id),
        'created_at': str(file.filename),
        'report_path': str(report_path.relative_to(BASE_DIR)),
    }
    _write_state(report_id, state_payload)

    background_tasks.add_task(_generate_report_task, report_id, str(upload_path), str(report_path))
    return JSONResponse(status_code=202, content={'report_id': report_id, 'status': 'processing'})

@app.post('/api/report/{report_id}/chat')
async def chat_with_report(report_id: str, message: dict):
    try:
        state = _read_state(report_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found.")

    if state["status"] != "completed":
        raise HTTPException(status_code=400, detail="Report is not ready for chat.")

    report_path = REPORT_DIR / f"{report_id}.pdf"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report PDF not found.")
    
    context_file_path = REPORT_DIR / f"{report_id}_context.json"
    if not context_file_path.exists():
         raise HTTPException(status_code=500, detail="Chat context data is missing.")
    with open(context_file_path, "r") as f:
        chat_context = json.load(f)
    chat_engine = PortfolioChatbot()
    user_message = message.get("message", "")
    try:
        # Call the chat method using the loaded data
        chat_response = chat_engine.chat(
            user_query=user_message,
            portfolio_json=chat_context["portfolio_json"],
            risk_metrics=chat_context["risk_metrics"],
            health_metrics=chat_context["health_metrics"],
            benchmark_metrics=chat_context["benchmark_metrics"],
            opportunity_result=chat_context["opportunity_result"]
        )

        return clean_markdown(chat_response["answer"])
    except Exception as exc:
        # Catch LLM timeouts or unexpected engine errors
        raise HTTPException(status_code=500, detail=f"Chat engine failed: {str(exc)}")


@app.get('/api/report/{report_id}/status')
async def get_report_status(report_id: str):
    try:
        state = _read_state(report_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='Report not found.')

    return state


@app.get('/api/report/{report_id}')
async def get_report(report_id: str):
    return await get_report_status(report_id)


def _generate_report_task(report_id: str, upload_path: str, report_path: str) -> None:
    try:
        enricher = PortfolioEnricher()
        risk_engine = RiskEngine()
        benchmark_engine = BenchmarkEngine()
        opportunity_engine = OpportunityEngine()
        health_engine = PortfolioHealthEngine()
        insight_engine = AIInsightEngine()

        portfolio_json = enricher.process_portfolio(
            source_type="excel",
            source_data=upload_path,
        )
        risk_metrics = risk_engine.evaluate_portfolio(portfolio_json)
        benchmark_metrics = benchmark_engine.compare_portfolio(portfolio_json)
        health_metrics = health_engine.calculate_health(
            portfolio_json,
            benchmark_metrics=benchmark_metrics,
        )
        opportunity_result = opportunity_engine.analyze(
            portfolio_json=portfolio_json,
            risk_metrics=risk_metrics,
            benchmark_metrics=benchmark_metrics,
            health_metrics=health_metrics,
        )
        insight_result = insight_engine.generate_insights(
            portfolio_json=portfolio_json,
            risk_metrics=risk_metrics,
            health_metrics=health_metrics,
            benchmark_metrics=benchmark_metrics,
            opportunity_result=opportunity_result,
        )
        chat_context = {
            "portfolio_json": portfolio_json,
            "risk_metrics": risk_metrics,
            "health_metrics": health_metrics,
            "benchmark_metrics": benchmark_metrics,
            "opportunity_result": opportunity_result
        }
        context_file_path = REPORT_DIR / f"{report_id}_context.json"
        with open(context_file_path, "w") as f:
            json.dump(chat_context, f)
        

        report_data = _build_report_data(
            upload_path=upload_path,
            report_id=report_id,
            portfolio_json=portfolio_json,
            risk_metrics=risk_metrics,
            benchmark_metrics=benchmark_metrics,
            health_metrics=health_metrics,
            opportunity_result=opportunity_result,
            insight_result=insight_result,
        )
        create_portfolio_pdf(report_path, report_data)

        overview = report_data['overview']
        state = _read_state(report_id)
        state.update(
            status='completed',
            portfolio_value=overview.get('Current Value'),
            health_score=overview.get('Health Score'),
            risk_level=overview.get('Risk Score'),
        )
        _write_state(report_id, state)
    except Exception as exc:
        state = _read_state(report_id)
        state.update(status='failed', error=str(exc))
        _write_state(report_id, state)


def _build_report_data(
    upload_path: str,
    report_id: str,
    portfolio_json: dict,
    risk_metrics: dict,
    benchmark_metrics: dict,
    health_metrics: dict,
    opportunity_result: dict,
    insight_result: dict,
) -> dict:
    file_name = Path(upload_path).stem
    investor = portfolio_json.get('client_name') or file_name.replace('_', ' ').title() or 'Portfolio Investor'

    summary = portfolio_json.get('summary', {}) or {}
    risk_summary = risk_metrics.get('risk_summary', {}) or {}
    portfolio_health = health_metrics.get('portfolio_health', {}) or {}
    portfolio_summary = risk_metrics.get('portfolio_summary', {}) or summary

    invested_value = _coerce_float(portfolio_summary.get('total_invested_value'))
    current_value = _coerce_float(portfolio_summary.get('total_live_value'))
    pnl_value = None if current_value is None or invested_value in (None, 0) else current_value - invested_value
    returns_pct = None if current_value is None or invested_value in (None, 0) else ((current_value - invested_value) / invested_value) * 100
    holdings = portfolio_json.get('holdings', []) or []
    risk_level = risk_summary.get('risk_level') or risk_summary.get('risk_score')
    health_score = portfolio_health.get('overall_score')

    return {
        'report_id': report_id,
        'created_at': None,
        'overview': {
            'Investor Name': investor,
            'Investment amount': _format_currency(invested_value),
            'Current Value': current_value,
            'PnL': _format_currency(pnl_value),
            'Returns': _format_percent(returns_pct),
            'Total Holdings': len(holdings),
            'Sectors': _derive_sectors(portfolio_json),
            'Risk Score': risk_level,
            'Health Score': _format_percent(health_score),
            'Benchmark': benchmark_metrics.get('benchmark_name') or benchmark_metrics.get('benchmark') or '-',
        },
        'analytics': {
            'portfolio_json': portfolio_json,
            'risk_metrics': risk_metrics,
            'benchmark_metrics': benchmark_metrics,
            'health_metrics': health_metrics,
            'opportunity_result': opportunity_result,
        },
        'ai_insights': insight_result,
    }

def clean_markdown(text: str) -> str:
    if not text:
        return ""
    
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("*", "")
    return text.strip()

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")