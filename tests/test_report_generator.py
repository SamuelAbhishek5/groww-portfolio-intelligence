from pathlib import Path

from backend.pdf.report_generator import _extract_metrics, _format_investor_profile, create_portfolio_pdf


def test_format_investor_profile_converts_decimal_confidence_to_percent():
    profile = {'type': 'Growth', 'confidence': 0.8, 'reason': 'Long-term capital appreciation'}

    rendered = _format_investor_profile(profile)

    assert '<b>Confidence:</b> 80%' in rendered


def test_extract_metrics_prefers_annualized_portfolio_return_for_graph_mapping():
    report_data = {
        'analytics': {
            'portfolio_json': {'summary': {'total_invested_value': 1000000, 'total_live_value': 1080000}},
            'risk_metrics': {'risk_summary': {'risk_score': 42.1, 'risk_level': 'Moderate'}},
            'benchmark_metrics': {
                'benchmark_return_pct': -0.06,
                'portfolio_return_pct': -19.59,
                'portfolio_weighted_return_pct': -2.49,
            },
            'health_metrics': {'portfolio_health': {'overall_score': 84.5, 'grade': 'A'}},
        }
    }

    metrics = _extract_metrics(report_data)

    assert metrics['portfolio_return_value'] == -19.59
    assert metrics['benchmark_return_value'] == -0.06


def test_create_portfolio_pdf_writes_output(tmp_path):
    report_data = {
        'report_id': 'RPT-001',
        'version': 'v2.0',
        'created_at': '2026-07-04 10:00 UTC',
        'overview': {
            'Investor Name': 'Ava Chen',
            'Current Value': '1250000',
            'Health Score': '84.5',
            'Risk Score': '42.1',
            'Benchmark': 'NIFTY 50',
            'Risk Level': 'Moderate',
        },
        'analytics': {
            'portfolio_json': {
                'summary': {'total_invested_value': 1000000, 'total_live_value': 1250000},
                'holdings': [
                    {'symbol': 'RELIANCE', 'weight_pct': 30, 'sector': 'Energy'},
                    {'symbol': 'TCS', 'weight_pct': 25, 'sector': 'Technology'},
                    {'symbol': 'HDFC', 'weight_pct': 20, 'sector': 'Financials'},
                ],
            },
            'risk_metrics': {
                'risk_summary': {
                    'risk_score': 42.1,
                    'risk_level': 'Moderate',
                    'portfolio_beta': 0.92,
                    'volatility': {'value_pct': 11.8},
                    'max_drawdown': {'percent': 8.5},
                    'sharpe_ratio': 1.24,
                    'diversification_score': 74.2,
                }
            },
            'benchmark_metrics': {
                'benchmark_name': 'NIFTY 50',
                'benchmark_return_pct': 8.5,
                'portfolio_weighted_return_pct': 12.4,
                'portfolio_relative_performance_pct': 3.9,
            },
            'health_metrics': {'portfolio_health': {'overall_score': 84.5, 'grade': 'A'}},
        },
        'ai_insights': {
            'executive_summary': 'The portfolio remains well balanced with strong quality exposure.',
            'portfolio_story': 'A disciplined and growth-oriented allocation profile.',
            'strengths': ['Balanced sector distribution'],
            'weaknesses': ['Limited international exposure'],
            'risk_commentary': 'Volatility remains manageable.',
            'performance_commentary': 'Performance is ahead of benchmark.',
            'benchmark_commentary': 'The portfolio has outperformed the benchmark.',
            'diversification_commentary': 'Diversification is healthy but can be improved further.',
            'priority_actions': ['Increase diversification', 'Trim concentration'],
            'future_outlook': 'The portfolio is positioned for steady compounding.',
            'investor_profile': {'type': 'Growth', 'confidence': 84, 'reason': 'Long-term capital appreciation'},
        },
    }

    output_path = tmp_path / 'portfolio_report.pdf'
    create_portfolio_pdf(str(output_path), report_data)

    assert output_path.exists()
    assert output_path.stat().st_size > 1000
