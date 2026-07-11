import io
import math
import re
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = Path(__file__).parent / "fonts"

pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_DIR / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_DIR / "DejaVuSans-Bold.ttf")))

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 2 * cm

TEXT_STYLE = ParagraphStyle(
    name='BodyWhite',
    fontName='DejaVu',
    fontSize=9.5,
    leading=12.5,
    textColor=colors.white,
)

TEXT_DARK_STYLE = ParagraphStyle(
    name='BodyDark',
    fontName='DejaVu',
    fontSize=9.5,
    leading=12.5,
    textColor=colors.HexColor('#24364f'),
)

TITLE_STYLE = ParagraphStyle(
    name='Title',
    fontName='DejaVu-Bold',
    fontSize=20,
    leading=24,
    textColor=colors.white,
)

SUBTITLE_STYLE = ParagraphStyle(
    name='Subtitle',
    fontName='DejaVu',
    fontSize=11,
    leading=14,
    textColor=colors.HexColor('#b8cfff'),
)

SECTION_STYLE = ParagraphStyle(
    name='Section',
    fontName='DejaVu-Bold',
    fontSize=12,
    leading=14,
    textColor=colors.white,
)

ACCENT_BLUE = colors.HexColor('#4a7cff')
ACCENT_GREEN = colors.HexColor("#16a91b")
ACCENT_RED = colors.HexColor('#ff6b6b')
ACCENT_DARKGREEN = colors.HexColor("#11710E")
ACCENT_AMBER = colors.HexColor('#ffb84d')
DARK_BG = colors.HexColor('#0f1f3e')
MIDNIGHT = colors.HexColor('#16294e')
MUTED = colors.HexColor('#697a96')
LIGHT_BG = colors.HexColor('#f4f7ff')


def _to_matplotlib_color(color: Any) -> Any:
    if color is None:
        return '#24364f'
    if isinstance(color, str):
        return color
    try:
        return (color.red, color.green, color.blue)
    except AttributeError:
        try:
            return color.getRGB()
        except AttributeError:
            return '#24364f'

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        # Save the current page state into memory before turning the page
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        # Now we know the total page count
        total_pages = len(self._saved_page_states)
        
        # Iterate through the saved pages and draw the dynamic elements
        for state in self._saved_page_states:
            self.__dict__.update(state)
            
            # --- FOOTER TEXT ---
            self.setFillColor(colors.HexColor('#24364f'))
            self.setFont('DejaVu', 7.5)
            
            # Grab the attributes we attached earlier
            report_id = getattr(self, 'report_id', 'REPORT-001')
            version = getattr(self, 'report_version', 'v1.0')
            
            # Build the combined string
            footer_text = f'Report ID: {report_id} | Version: {version} | Page {self._pageNumber} of {total_pages}'
            
            # Draw it on the left side of the footer
            margin_cm = 2.0 * cm
            self.drawString(margin_cm + 0.25 * cm, margin_cm - 0.14 * cm, footer_text)            
            super().showPage()
            
        super().save()
def _handle_page_break(pdf_canvas: canvas.Canvas, current_y: float, required_height: float) -> float:
    # Check if the element overlaps the bottom footer margin
    if current_y - required_height < MARGIN + 0.8 * cm:
        _draw_page_header_footer(pdf_canvas)  # Draw decorations before turning page
        pdf_canvas.showPage()
        # Return new Y position slightly below the top header
        return PAGE_HEIGHT - MARGIN - 1.2 * cm
    return current_y
def create_portfolio_pdf(target_path: str, report_data: dict) -> None:
    target_file = Path(target_path)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    pdf_canvas = NumberedCanvas(str(target_file), pagesize=A4)
    pdf_canvas.report_id = report_data.get('report_id') or 'REPORT-001'
    pdf_canvas.report_version = report_data.get('version') or 'v1.0'
    add_cover_page(pdf_canvas, report_data)
    add_portfolio_overview_page(pdf_canvas, report_data)
    add_visualization_page(pdf_canvas, report_data)
    add_ai_insights_page(pdf_canvas, report_data)
    pdf_canvas.save()


def add_cover_page(pdf_canvas: canvas.Canvas, report_data: dict) -> None:
    metrics = _extract_metrics(report_data)
    overview = report_data.get('overview', {}) or {}
    ai_insights = report_data.get('ai_insights', {}) or {}

    pdf_canvas.setFillColor(DARK_BG)
    pdf_canvas.rect(MARGIN - 0.4 * cm, MARGIN - 0.4 * cm, PAGE_WIDTH - 2 * MARGIN + 0.8 * cm, PAGE_HEIGHT - 2 * MARGIN + 0.8 * cm, fill=1, stroke=0)

    pdf_canvas.setFillColor(colors.HexColor('#132446'))
    pdf_canvas.roundRect(MARGIN, PAGE_HEIGHT - MARGIN - 4.4 * cm, PAGE_WIDTH - 2 * MARGIN, 3.3 * cm, 16, fill=1, stroke=0)

    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.setFont('DejaVu-Bold', 22)
    pdf_canvas.drawString(MARGIN + 0.6 * cm, PAGE_HEIGHT - MARGIN - 1.5 * cm, 'Groww Portfolio Intelligence Report')
    pdf_canvas.setFont('DejaVu', 11)
    pdf_canvas.setFillColor(colors.HexColor('#b8cfff'))
    pdf_canvas.drawString(MARGIN + 0.6 * cm, PAGE_HEIGHT - MARGIN - 2.2 * cm, 'Executive portfolio intelligence for disciplined, advisor-grade review')

    logo_x = PAGE_WIDTH - MARGIN - 3.4 * cm
    logo_y = PAGE_HEIGHT - MARGIN - 4.5 * cm
    pdf_canvas.setFillColor(colors.HexColor('#1f3d72'))
    pdf_canvas.roundRect(logo_x, logo_y, 3.4 * cm, 2.2 * cm, 12, fill=1, stroke=0)
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.setFont('DejaVu-Bold', 14)
    pdf_canvas.drawCentredString(logo_x + 1.7 * cm, logo_y + 0.85 * cm, 'GROWW')

    pdf_canvas.setFillColor(colors.HexColor('#b8cfff'))
    pdf_canvas.setFont('DejaVu', 10)
    timestamp = report_data.get('created_at') or datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    pdf_canvas.drawString(MARGIN + 0.6 * cm, PAGE_HEIGHT - MARGIN - 4.0 * cm, f'Generated at {timestamp}')

    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.setFont('DejaVu-Bold', 12)
    pdf_canvas.drawString(MARGIN + 0.6 * cm, PAGE_HEIGHT - MARGIN - 6.6 * cm, 'Investor')
    pdf_canvas.setFont('DejaVu-Bold', 16)
    pdf_canvas.drawString(MARGIN + 0.6 * cm, PAGE_HEIGHT - MARGIN - 7.5 * cm, _safe_text(overview.get('Investor Name') or metrics['investor_name']))

    cards = [
        ('Portfolio Value', metrics['current_value_display'], colors.HexColor('#8b5cf6')),
        ('Total Return', metrics['return_display'], ACCENT_RED),
        ('Health Score', metrics['health_score_display'], ACCENT_GREEN),
        ('Portfolio Grade', metrics['health_grade'], ACCENT_BLUE),
        ('Risk Level', metrics['risk_level'], ACCENT_AMBER),
        ('Holdings', str(metrics['holding_count']), colors.HexColor('#3b82f6')),
        ('Benchmark', metrics['benchmark_name'], colors.HexColor('#12b981')),
    ]

    card_width = 2.9 * cm
    card_height = 1.7 * cm
    x = MARGIN + 0.25 * cm
    y = PAGE_HEIGHT - MARGIN - 10.0 * cm
    for idx, (label, value, color) in enumerate(cards):
        if idx % 3 == 0 and idx != 0:
            x = MARGIN + 0.25 * cm
            y -= 2.2 * cm
        pdf_canvas.setFillColor(colors.HexColor('#14284a'))
        pdf_canvas.roundRect(x, y, card_width, card_height, 10, fill=1, stroke=0)
        pdf_canvas.setFillColor(color)
        pdf_canvas.setFont('DejaVu-Bold', 9)
        pdf_canvas.drawString(x + 0.2 * cm, y + 0.95 * cm, label)
        pdf_canvas.setFont('DejaVu-Bold', 12)
        pdf_canvas.drawString(x + 0.2 * cm, y + 0.25 * cm, _safe_text(value))
        x += card_width + 0.2 * cm

    summary_text = _safe_text(
        ai_insights.get("executive_summary")
        or "The portfolio narrative is derived from the supplied analytics and AI-generated insight engine."
    ).replace(" - ", " • ")
    TEXT_STYLE = ParagraphStyle("Summary",
        parent=getSampleStyleSheet()["BodyText"],
        fontName="DejaVu",
        fontSize=10,
        leading=14,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
    paragraph = Paragraph(summary_text, TEXT_STYLE)

    available_width = PAGE_WIDTH - 2 * MARGIN - 1.1 * cm

    # Measure paragraph height
    _, para_height = paragraph.wrap(available_width, 10000)

    title_height = 0.9 * cm
    top_padding = 0.55 * cm
    bottom_padding = 0.9 * cm
    footer_height = 0.5 * cm

    box_height = (
        title_height +
        para_height +
        top_padding +
        bottom_padding +
        footer_height
    )

    summary_box_y = MARGIN + 0.8 * cm

    # Background
    pdf_canvas.setFillColor(colors.HexColor("#132446"))
    pdf_canvas.roundRect(
        MARGIN,
        summary_box_y,
        PAGE_WIDTH - 2 * MARGIN,
        box_height,
        16,
        fill=1,
        stroke=0,
    )

    # Title
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.setFont("DejaVu-Bold", 13)
    pdf_canvas.drawString(
        MARGIN + 0.55 * cm,
        summary_box_y + box_height - 0.8 * cm,
        "Executive Summary"
    )
    
    # Paragraph
    frame_y = summary_box_y + footer_height + bottom_padding
    summary_frame = Frame(
        MARGIN + 0.55 * cm,
        frame_y,
        available_width,
        para_height,
        leftPadding=0,    # Remove default 6pt padding so the calculated height works
        bottomPadding=0,
        rightPadding=0,
        topPadding=0,
        showBoundary=0,   # Set to 0 to remove the debug border
    )
    
    summary_frame.addFromList([paragraph], pdf_canvas)

    # Footer
    pdf_canvas.setFillColor(colors.HexColor("#8ec5ff"))
    pdf_canvas.setFont("DejaVu", 9)
    pdf_canvas.drawString(
        MARGIN + 0.55 * cm,
        summary_box_y + 0.25 * cm,
        "Confidential • AI-generated advisory context • For portfolio review only"
    )

    _draw_page_header_footer(pdf_canvas)
    pdf_canvas.showPage()


def add_portfolio_overview_page(pdf_canvas: canvas.Canvas, report_data: dict) -> None:
    metrics = _extract_metrics(report_data)
    pdf_canvas.setFillColor(LIGHT_BG)
    pdf_canvas.rect(MARGIN - 0.4 * cm, MARGIN - 0.4 * cm, PAGE_WIDTH - 2 * MARGIN + 0.8 * cm, PAGE_HEIGHT - 2 * MARGIN + 0.8 * cm, fill=1, stroke=0)

    pdf_canvas.setFillColor(DARK_BG)
    pdf_canvas.roundRect(MARGIN, PAGE_HEIGHT - MARGIN - 1.2 * cm, PAGE_WIDTH - 2 * MARGIN, 0.6 * cm, 8, fill=1, stroke=0)
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.setFont('DejaVu-Bold', 16)
    pdf_canvas.drawString(MARGIN + 0.4 * cm, PAGE_HEIGHT - MARGIN - 1.0 * cm, 'Portfolio Overview Dashboard')

    card_width = 7.8 * cm
    card_height = 2.1 * cm
    gap = 0.4 * cm
    start_x = MARGIN + 0.2 * cm
    start_y = PAGE_HEIGHT - MARGIN - 4.6 * cm

    paired_metrics = [
        ('Investment Amount', metrics['investment_amount_display'], 'Current Value', metrics['current_value_display'], ACCENT_BLUE),
        ('Unrealised P&L', metrics['pnl_display'], 'Return', metrics['return_display'], ACCENT_RED),
        ('Risk Level', metrics['risk_level'], 'Beta', metrics['portfolio_beta_display'], ACCENT_AMBER),
        ('Volatility', metrics['volatility_display'], 'Sharpe Ratio', metrics['sharpe_display'], ACCENT_GREEN),
    ]

    for index, (left_label, left_value, right_label, right_value, color) in enumerate(paired_metrics):
        x = start_x if index % 2 == 0 else start_x + card_width + gap
        y = start_y - (index // 2) * (card_height + gap)
        pdf_canvas.setFillColor(colors.white)
        pdf_canvas.roundRect(x, y, card_width, card_height, 10, fill=1, stroke=0)
        pdf_canvas.setFillColor(color)
        pdf_canvas.setFont('DejaVu-Bold', 8.5)
        pdf_canvas.drawString(x + 0.25 * cm, y + 1.23 * cm, left_label)
        pdf_canvas.setFont('DejaVu-Bold', 11)
        pdf_canvas.drawString(x + 0.25 * cm, y + 0.45 * cm, _safe_text(left_value))
        pdf_canvas.setFillColor(DARK_BG)
        pdf_canvas.drawString(x + 4.2 * cm, y + 1.23 * cm, right_label)
        pdf_canvas.setFont('DejaVu-Bold', 10)
        pdf_canvas.drawString(x + 4.2 * cm, y + 0.45 * cm, _safe_text(right_value))

    health_box_y = MARGIN + 1.2 * cm
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.roundRect(MARGIN + 0.2 * cm, health_box_y, PAGE_WIDTH - 2 * MARGIN - 0.4 * cm, 4.8 * cm, 12, fill=1, stroke=0)
    pdf_canvas.setFillColor(DARK_BG)
    pdf_canvas.setFont('DejaVu-Bold', 12)
    pdf_canvas.drawString(MARGIN + 0.5 * cm, health_box_y + 4.1 * cm, 'Portfolio Health Breakdown')

    components = [
        ('Risk Score', metrics['risk_score_value'], ACCENT_RED),
        ('Performance', metrics['performance_component'], ACCENT_GREEN),
        ('Diversification', metrics['diversification_component'], ACCENT_BLUE),
        ('Quality', metrics['quality_component'], ACCENT_AMBER),
    ]
    bar_y = health_box_y + 2.8 * cm
    for label, value, color in components:
        _draw_progress_bar(pdf_canvas, MARGIN + 0.55 * cm, bar_y, PAGE_WIDTH - 2 * MARGIN - 1.1 * cm, 0.50 * cm, label, value, color)
        bar_y -= 0.7 * cm

    benchmark_box_y = MARGIN + 6.5 * cm
    pdf_canvas.setFillColor(colors.HexColor('#f5f8ff'))
    pdf_canvas.roundRect(MARGIN + 0.2 * cm, benchmark_box_y, PAGE_WIDTH - 2 * MARGIN - 0.4 * cm, 5.0 * cm, 12, fill=1, stroke=0)
    pdf_canvas.setFillColor(DARK_BG)
    pdf_canvas.setFont('DejaVu-Bold', 11)
    pdf_canvas.drawString(MARGIN + 0.5 * cm, benchmark_box_y + 2.6 * cm, 'Benchmark Comparison(2 years)')
    pdf_canvas.setFillColor(MUTED)
    pdf_canvas.setFont('DejaVu', 9)
    benchmark_rows = [
        ['Portfolio Return', metrics['portfolio_performance_display'], 'Benchmark Return', metrics['benchmark_performance_display']],
        ['Annualized Excess Return ', metrics['alpha_display'], 'Tracking Error', metrics['tracking_error_display']],
        ['Information Ratio', metrics['information_ratio_display'], 'Rating', metrics['benchmark_rating']],
    ]
    table_data = [
    ['Portfolio Return', metrics['portfolio_performance_display']],
    ['Benchmark Return', metrics['benchmark_performance_display']],
    ['Annualized Excess Return ', metrics['alpha_display']],
    ['Rating', metrics['benchmark_rating']]]
    benchmark_table = Table(table_data,colWidths=[4.0 * cm, 2.8 * cm],rowHeights=[0.45 * cm] * len(table_data),)
    #benchmark_table = Table(
    #    [[label, value] for label, value in [(row[0], row[1]) for row in benchmark_rows] + [('Information Ratio', benchmark_rows[2][1]), ('Rating', benchmark_rows[2][3])]],
    #    colWidths=[3.2 * cm, 2.4 * cm],
    #    rowHeights=[0.45 * cm, 0.45 * cm, 0.45 * cm, 0.45 * cm],
    #)
    benchmark_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'DejaVu'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0.15 * cm),
        ('TOPPADDING', (0, 0), (-1, -1), 0.02 * cm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.02 * cm),
    ]))
    benchmark_table.wrapOn(pdf_canvas, PAGE_WIDTH, PAGE_HEIGHT)
    benchmark_table.drawOn(pdf_canvas, MARGIN + 0.5 * cm, benchmark_box_y + 0.35 * cm)
    
    _draw_page_header_footer(pdf_canvas)
    pdf_canvas.showPage()


def add_visualization_page(pdf_canvas: canvas.Canvas, report_data: dict) -> None:
    metrics = _extract_metrics(report_data)
    pdf_canvas.setFillColor(LIGHT_BG)
    pdf_canvas.rect(MARGIN - 0.4 * cm, MARGIN - 0.4 * cm, PAGE_WIDTH - 2 * MARGIN + 0.8 * cm, PAGE_HEIGHT - 2 * MARGIN + 0.8 * cm, fill=1, stroke=0)

    pdf_canvas.setFillColor(DARK_BG)
    pdf_canvas.roundRect(MARGIN, PAGE_HEIGHT - MARGIN - 1.1 * cm, PAGE_WIDTH - 2 * MARGIN, 0.6 * cm, 8, fill=1, stroke=0)
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.setFont('DejaVu-Bold', 16)
    pdf_canvas.drawString(MARGIN + 0.4 * cm, PAGE_HEIGHT - MARGIN - 1.0 * cm, 'Portfolio Visualisations')

    chart_width = 5.4 * cm
    chart_height = 4.6 * cm
    left = MARGIN + 0.25 * cm
    top = PAGE_HEIGHT - MARGIN - 4.4 * cm

    _draw_chart_image(pdf_canvas, left, top, chart_width, chart_height, _build_pie_chart_image('Holding Allocation', metrics['holding_allocation']))
    _draw_chart_image(pdf_canvas, left + 5.8 * cm, top, chart_width, chart_height, _build_pie_chart_image('Sector Allocation', metrics['sector_allocation']))
    _draw_chart_image(pdf_canvas, left + 11.6 * cm, top, chart_width, chart_height, _build_portfolio_health_indicator_image('Portfolio Health', metrics['health_score_value']))

    _draw_chart_image(pdf_canvas, left, top - 4.9 * cm, chart_width, chart_height,_build_risk_indicator_image('Risk Score', metrics['risk_score_value']))
    _draw_chart_image(pdf_canvas, left + 5.8 * cm, top - 4.9 * cm, chart_width, chart_height, _build_bar_chart_image('Portfolio vs Benchmark', [('Portfolio', metrics['portfolio_return_value']), ('Benchmark', metrics['benchmark_return_value'])], [ACCENT_BLUE, ACCENT_AMBER]))
    _draw_chart_image(pdf_canvas, left + 11.6 * cm, top - 4.9 * cm, chart_width, chart_height, _build_bar_chart_image('Top Holdings', metrics['top_holdings'], [ACCENT_BLUE, ACCENT_GREEN, ACCENT_AMBER, ACCENT_RED, colors.HexColor('#8b5cf6')]))

    _draw_chart_image(pdf_canvas, left, top - 9.8 * cm, chart_width, chart_height, _build_bar_chart_image('Sector Exposure', metrics['sector_exposure'], [ACCENT_AMBER, ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, colors.HexColor('#8b5cf6')]))
    _draw_chart_image(pdf_canvas, left + 5.8 * cm, top - 9.8 * cm, chart_width, chart_height, _build_radar_chart_image('Diversification Radar', metrics['diversification_axes']))
    _draw_chart_image(pdf_canvas, left + 11.6 * cm, top - 9.8 * cm, chart_width, chart_height, _build_metric_cards_image(metrics))

    _draw_page_header_footer(pdf_canvas)
    pdf_canvas.showPage()


def add_ai_insights_page(pdf_canvas: canvas.Canvas, report_data: dict) -> None:
    ai_insights = report_data.get('ai_insights', {}) or {}
    metrics = _extract_metrics(report_data)
    y_position = PAGE_HEIGHT - MARGIN - 1.0 * cm

    y_position = _draw_text_card(pdf_canvas, 'Executive Summary', _safe_text(ai_insights.get('executive_summary') or 'The portfolio narrative is derived from the supplied analytics and AI-generated insight engine.'), y_position, full_width=True, bg_color=colors.HexColor('#153b67'))
    y_position = _draw_text_card(pdf_canvas, 'Portfolio Story', _safe_text(ai_insights.get('portfolio_story') or 'The portfolio profile reflects a balanced growth-oriented stance.'), y_position, full_width=True, bg_color=colors.HexColor('#24507d'))
    y_position = _draw_bullet_card(pdf_canvas, 'Key Findings', _build_key_findings(ai_insights, metrics), y_position, bg_color=colors.HexColor('#174d34'))
    y_position = _draw_bullet_card(pdf_canvas, 'Risk Commentary', _build_list_from_field(ai_insights.get('risk_commentary')), y_position, bg_color=colors.HexColor('#6a2430'))
    y_position = _draw_bullet_card(pdf_canvas, 'Performance Commentary', _build_list_from_field(ai_insights.get('performance_commentary')), y_position, bg_color=colors.HexColor('#1e4a6e'))
    y_position = _draw_bullet_card(pdf_canvas, 'Benchmark Commentary', _build_list_from_field(ai_insights.get('benchmark_commentary')), y_position, bg_color=colors.HexColor('#715b1f'))
    y_position = _draw_bullet_card(pdf_canvas, 'Diversification Commentary', _build_list_from_field(ai_insights.get('diversification_commentary')), y_position, bg_color=colors.HexColor('#2d4f4a'))

    y_position = _draw_list_card(pdf_canvas, 'Priority Actions', _build_priority_actions(ai_insights, metrics), y_position, full_width=True, bg_color=colors.HexColor('#183b67'))
    y_position = _draw_text_card(pdf_canvas, 'Future Outlook', _safe_text(ai_insights.get('future_outlook') or 'The portfolio remains well positioned for long-term compounding.'), y_position, full_width=True, bg_color=colors.HexColor('#1e3a5f'))
    y_position = _draw_text_card(pdf_canvas, 'Investor Profile', _format_investor_profile(ai_insights.get('investor_profile')), y_position, full_width=True, bg_color=colors.HexColor('#1e3a5f'))

    holding_insights = ai_insights.get('holding_insights') or _build_fallback_holding_insights(report_data, metrics)
    if holding_insights:
        y_position = _draw_section_heading(pdf_canvas, 'Holding Insights', y_position)
        for insight in holding_insights:
            y_position = _draw_holding_card(pdf_canvas, insight, y_position)

    sector_insights = ai_insights.get('sector_insights') or _build_fallback_sector_insights(report_data, metrics)
    if sector_insights:
        y_position = _draw_section_heading(pdf_canvas, 'Sector Insights', y_position)
        for insight in sector_insights:
            y_position = _draw_sector_card(pdf_canvas, insight, y_position)

    _draw_page_header_footer(pdf_canvas)
    pdf_canvas.showPage()


def _draw_chart_image(pdf_canvas: canvas.Canvas, x: float, y: float, width: float, height: float, image_bytes: bytes) -> None:
    if not image_bytes:
        return
    pdf_canvas.drawImage(ImageReader(io.BytesIO(image_bytes)), x, y - height, width=width, height=height, preserveAspectRatio=True, mask='auto')


def _build_pie_chart_image(title: str, data: List[Tuple[str, float]]) -> bytes:
    fig, ax = plt.subplots(figsize=(3.8, 2.8), dpi=170)
    fig.patch.set_facecolor(_to_matplotlib_color(LIGHT_BG))
    ax.set_facecolor(_to_matplotlib_color(LIGHT_BG))

    labels = [label for label, value in data if value]
    values = [value for _, value in data if value]
    palette = [ACCENT_BLUE, ACCENT_GREEN, ACCENT_AMBER, ACCENT_RED, colors.HexColor('#8b5cf6'), colors.HexColor('#3b82f6')]
    chart_colors = [_to_matplotlib_color(item) for item in palette[:len(values)]]

    if not values:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', fontsize=10, color='#24364f')
        ax.set_xticks([])
        ax.set_yticks([])
    else:
        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=chart_colors, pctdistance=0.6, textprops={'fontsize':7, 'color':'#24364f'})

    ax.set_title(title, fontsize=10, color='#24364f', pad=10)
    ax.axis('equal')
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format='png', dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    return buffer.getvalue()


def _build_bar_chart_image(title: str, data: List[Tuple[str, float]], colors_list: List[Any]) -> bytes:
    fig, ax = plt.subplots(figsize=(3.8, 2.8), dpi=170)
    fig.patch.set_facecolor(_to_matplotlib_color(LIGHT_BG))
    ax.set_facecolor(_to_matplotlib_color(LIGHT_BG))

    labels = [label for label, value in data if value is not None]
    values = [value for _, value in data if value is not None]
    chart_colors = [_to_matplotlib_color(item) for item in colors_list[:len(values)]]
    
    bar_width = 0.55 if len(values) <= 2 else 0.8
    bars = ax.bar(labels, values, color=chart_colors, edgecolor='none', width=bar_width)
    
    ax.set_title(title, fontsize=10, color='#24364f', pad=10)
    ax.set_ylabel('Value', fontsize=8, color='#24364f')
    
    ax.bar_label(bars, fmt='%g', padding=3, fontsize=7, color='#24364f', fontweight='bold')
    
    # 2. Add subtle horizontal grid lines for better visual scale reference
    ax.yaxis.grid(True, linestyle='--', which='major', color='#d4dde8', alpha=0.6)
    ax.set_axisbelow(True) # Ensures grid lines are drawn behind the bars
    
    # 3. Rotate x-axis labels slightly if there are many bars to prevent overlapping text
    if len(labels) > 3:
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#d4dde8')
    ax.spines['bottom'].set_color('#d4dde8')
    ax.tick_params(colors='#24364f', labelsize=7)
    
    if not values:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes, fontsize=10, color='#24364f')
        
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format='png', dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    
    return buffer.getvalue()



def _build_risk_indicator_image(title: str, value: Optional[float]) -> bytes:
    fig, ax = plt.subplots(figsize=(3.8, 2.8), dpi=170)
    
    # Assuming LIGHT_BG is defined in your file, replace '#ffffff' if needed
    bg_color = '#ffffff' 
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    safe_value = max(0.0, min(100.0, float(value or 0.0)))

    # 1. Dynamic Color Logic
    if safe_value < 33.3:
        indicator_color = '#4CAF50'  # Green for Low Risk
    elif safe_value < 66.6:
        indicator_color = '#ffa64d'  # Orange for Moderate Risk
    else:
        indicator_color = '#ff4d4d'  # Red for High Risk

    # 2. Half-Circle Gauge Logic
    # We use a total pie size of 200. The first 100 is the visible top half, 
    # and the last 100 is the invisible bottom half.
    sizes = [safe_value, 100 - safe_value, 100]
    
    # 'none' makes the bottom half completely transparent
    colors = [indicator_color, '#e8edf7', 'none'] 

    ax.pie(sizes, colors=colors, startangle=180, counterclock=False, 
           wedgeprops={'width': 0.35, 'edgecolor': bg_color, 'linewidth': 2})
    
    # 3. Text Positioning
    # Adjusted to sit perfectly inside the arch of the half-circle
    ax.text(0, -0.1, f'{safe_value:.0f}', ha='center', va='center', fontsize=22, color='#24364f', fontweight='bold')
    ax.text(0, -0.35, title, ha='center', va='center', fontsize=11, color='#24364f')
    
    ax.set_aspect('equal')
    ax.axis('off')
    
    buffer = io.BytesIO()
    fig.tight_layout()
    # transparent=True ensures the bottom half doesn't block other PDF elements
    fig.savefig(buffer, format='png', dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor(), transparent=True)
    plt.close(fig)
    
    return buffer.getvalue()
def _build_portfolio_health_indicator_image(title: str, value: Optional[float]) -> bytes:
    fig, ax = plt.subplots(figsize=(3.8, 2.8), dpi=170)
    
    # Assuming LIGHT_BG is defined in your file, replace '#ffffff' if needed
    bg_color = '#ffffff' 
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    safe_value = max(0.0, min(100.0, float(value or 0.0)))

    # Dynamic Color Logic for Portfolio Health
    if safe_value < 33.3:
        indicator_color = '#ff4d4d'  # Red for Poor Health
    elif safe_value < 66.6:
        indicator_color = '#ffa64d'  # Orange for Moderate Health
    else:
        indicator_color = '#4CAF50'  # Green for Good Health

    sizes = [safe_value, 100 - safe_value, 100]
    colors = [indicator_color, '#e8edf7', 'none'] 

    ax.pie(sizes, colors=colors, startangle=180, counterclock=False, 
           wedgeprops={'width': 0.35, 'edgecolor': bg_color, 'linewidth': 2})
    
    ax.text(0, -0.1, f'{safe_value:.0f}', ha='center', va='center', fontsize=22, color='#24364f', fontweight='bold')
    ax.text(0, -0.35, title, ha='center', va='center', fontsize=11, color='#24364f')
    
    ax.set_aspect('equal')
    ax.axis('off')
    
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format='png', dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor(), transparent=True)
    plt.close(fig)
    
    return buffer.getvalue()

def _build_radar_chart_image(title: str, axes: List[Tuple[str, float]]) -> bytes:
    fig, ax = plt.subplots(figsize=(3.8, 2.8), dpi=170, subplot_kw={'polar': True})
    fig.patch.set_facecolor(_to_matplotlib_color(LIGHT_BG))
    ax.set_facecolor(_to_matplotlib_color(LIGHT_BG))
    if not axes:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes, fontsize=10)
    else:
        labels = [label for label, _ in axes]
        values = [max(0.0, min(100.0, float(value))) for _, value in axes]
        angles = [index * (2 * math.pi / len(labels)) for index in range(len(labels))]
        angles += angles[:1]
        values += values[:1]
        ax.plot(angles, values, color=_to_matplotlib_color(ACCENT_BLUE), linewidth=1.8)
        ax.fill(angles, values, color=_to_matplotlib_color(ACCENT_BLUE), alpha=0.2)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_ylim(0, 100)
        ax.set_yticklabels([])
    ax.set_title(title, fontsize=10, color='#24364f', pad=20)
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format='png', dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    return buffer.getvalue()


def _build_metric_cards_image(metrics: dict) -> bytes:
    fig, ax = plt.subplots(figsize=(3.8, 2.8), dpi=170)
    fig.patch.set_facecolor(_to_matplotlib_color(LIGHT_BG))
    ax.set_facecolor(_to_matplotlib_color(LIGHT_BG))
    ax.axis('off')
    ax.text(0.05, 0.1, 'Risk Metrics Summary', fontsize=10, color='#24364f', fontweight='bold',va='center')

    text = [
        ('Volatility', metrics['volatility_display']),
        ('Max Drawdown', metrics['drawdown_display']),
        ('Sharpe Ratio', metrics['sharpe_display']),
        ('Beta', metrics['portfolio_beta_display']),
    ]
    y = 0.8
    for label, value in text:
        ax.text(0.05, y, label, fontsize=9, color='#24364f', fontweight='bold', va='center')
        ax.text(0.72, y, value, fontsize=9, color=_to_matplotlib_color(ACCENT_BLUE), va='center')
        y -= 0.2
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format='png', dpi=160, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    return buffer.getvalue()


def _draw_text_card(pdf_canvas: canvas.Canvas, title: str, body: str, y: float, full_width: bool = False, bg_color: Any = DARK_BG) -> float:
    width = PAGE_WIDTH - (2 * MARGIN)
    if not full_width:
        width = (PAGE_WIDTH - (2 * MARGIN) - 0.35 * cm) / 2
    height = _estimate_card_height(pdf_canvas, body, width - 0.5 * cm)
    height = max(height + 0.9 * cm, 2.4 * cm)
    y = _handle_page_break(pdf_canvas, y, height)

    x = MARGIN
    if not full_width:
        x = MARGIN if y < PAGE_HEIGHT - MARGIN - 2.5 * cm else MARGIN + width + 0.35 * cm
        
    pdf_canvas.setFillColor(bg_color)
    pdf_canvas.roundRect(x, y - height, width, height, 10, fill=1, stroke=0)
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.setFont('DejaVu-Bold', 10.5)
    pdf_canvas.drawString(x + 0.25 * cm, y - 0.4 * cm, title)

    paragraph = Paragraph(body, TEXT_STYLE)
    
    # FIX 2: Set all internal Frame paddings to 0 so your manual math works correctly
    frame = Frame(
        x + 0.25 * cm, 
        y - height + 0.25 * cm, 
        width - 0.5 * cm, 
        height - 0.8 * cm, 
        showBoundary=0,
        leftPadding=0, 
        bottomPadding=0, 
        rightPadding=0, 
        topPadding=0
    )
    
    frame.addFromList([paragraph], pdf_canvas)
    return y - height - 0.25 * cm


def _draw_bullet_card(pdf_canvas: canvas.Canvas, title: str, items: List[Any], y: float, bg_color: Any = DARK_BG) -> float:
    content = '<br/>'.join([f'• {item}' for item in items if str(item).strip()]) if items else 'No commentary available.'
    return _draw_text_card(pdf_canvas, title, content, y, full_width=True, bg_color=bg_color)


def _draw_list_card(pdf_canvas: canvas.Canvas, title: str, items: List[Any], y: float, full_width: bool = False, bg_color: Any = DARK_BG) -> float:
    content = '<br/>'.join([f'• {item}' for item in items if str(item).strip()]) if items else 'No actions available.'
    return _draw_text_card(pdf_canvas, title, content, y, full_width=full_width, bg_color=bg_color)


def _build_fallback_holding_insights(report_data: dict, metrics: dict) -> List[dict]:
    analytics = report_data.get('analytics', {}) or {}
    portfolio_json = analytics.get('portfolio_json', {}) or {}
    holdings = list(portfolio_json.get('holdings', []) or [])
    if not holdings:
        return []

    ranked_holdings = sorted(
        holdings,
        key=lambda item: (_coerce_float(item.get('weight_pct')) if _coerce_float(item.get('weight_pct')) is not None else _coerce_float(item.get('weight')) or 0.0),
        reverse=True,
    )[:2]

    insights = []
    for holding in ranked_holdings:
        symbol = holding.get('symbol') or holding.get('name') or 'Holding'
        sector = holding.get('sector') or 'Unassigned'
        weight = _coerce_float(holding.get('weight_pct'))
        if weight is None:
            weight = _coerce_float(holding.get('weight'))
        if weight is None:
            weight = _coerce_float(holding.get('allocation_pct'))
        weight_text = f'{weight:.1f}%' if weight is not None else 'a meaningful allocation'
        insights.append({
            'company': symbol,
            'symbol': symbol,
            'analysis': f'{symbol} currently carries {weight_text} of the portfolio and contributes directly to the overall allocation profile.',
            'strengths': [f'Meaningful portfolio exposure in {sector}', 'Supports the current investment thesis'],
            'risks': ['Concentration risk can increase if sizing expands further'],
            'recommendation': [f'Keep sizing disciplined around {weight_text}', 'Rebalance into complementary holdings if concentration rises'],
        })
    return insights


def _build_fallback_sector_insights(report_data: dict, metrics: dict) -> List[dict]:
    analytics = report_data.get('analytics', {}) or {}
    portfolio_json = analytics.get('portfolio_json', {}) or {}
    holdings = list(portfolio_json.get('holdings', []) or [])
    if not holdings:
        return []

    sector_map: dict = {}
    for holding in holdings:
        sector = holding.get('sector') or 'Unassigned'
        weight = _coerce_float(holding.get('weight_pct'))
        if weight is None:
            weight = _coerce_float(holding.get('weight'))
        if weight is None:
            weight = _coerce_float(holding.get('allocation_pct'))
        if weight is None:
            continue
        sector_map[sector] = sector_map.get(sector, 0.0) + float(weight)

    insights = []
    for sector, value in sorted(sector_map.items(), key=lambda item: item[1], reverse=True)[:2]:
        insights.append({
            'sector': sector,
            'analysis': f'{sector} represents {value:.1f}% of the portfolio and is a meaningful driver of performance.',
            'strengths': ['Provides clear thematic exposure', 'Adds diversification when balanced'],
            'risks': ['Sector concentration may amplify downside moves'],
            'recommendation': ['Maintain balanced allocations and monitor correlation', 'Reassess sizing if the sector becomes too dominant'],
        })
    return insights


def _get_placeholder_text(value: Any, fallback: str) -> str:
    text = _safe_text(value).strip()
    if text in ('', '-', 'Not available', 'None', 'none'):
        return fallback
    return text


def _draw_holding_card(pdf_canvas: canvas.Canvas, insight: dict, y: float) -> float:
    company = _safe_text(insight.get('company') or insight.get('symbol') or 'Holding')
    symbol = _safe_text(insight.get('symbol') or '')
    if company and symbol and company != symbol:
        title = f'{company} ({symbol})'
    else:
        title = company or symbol or 'Holding'
    body = (
        f"<b>Analysis:</b> {_get_placeholder_text(insight.get('analysis') or insight.get('summary'), 'The position contributes meaningfully to the portfolio allocation profile and should be monitored for concentration risk.')}<br/>"
        f"<b>Strengths:</b> {_get_placeholder_text(_join_values(insight.get('strengths', [])), 'The holding supports a balanced quality profile with durable exposure.')}<br/>"
        f"<b>Risks:</b> {_get_placeholder_text(_join_values(insight.get('risks', [])), 'Concentration and sector sensitivity should be monitored as the position evolves.')}<br/>"
        f"<b>Recommendation:</b> {_get_placeholder_text(insight.get('recommendation'), 'Maintain disciplined sizing and review rebalance thresholds periodically.')}"
    )
    return _draw_text_card(pdf_canvas, title, body, y, full_width=True, bg_color=colors.HexColor('#183b67'))


def _draw_sector_card(pdf_canvas: canvas.Canvas, insight: dict, y: float) -> float:
    title = _safe_text(insight.get('sector') or 'Sector')
    body = (
        f"<b>Analysis:</b> {_get_placeholder_text(insight.get('analysis') or insight.get('summary'), 'The sector remains a meaningful contributor to portfolio exposure and should be balanced carefully.')}<br/>"
        f"<b>Recommendation:</b> {_get_placeholder_text(insight.get('recommendation'), 'Monitor sizing and correlation to preserve diversification and resilience.') }"
    )
    return _draw_text_card(pdf_canvas, title, body, y, full_width=True, bg_color=colors.HexColor('#1f4f4a'))


def _draw_section_heading(pdf_canvas: canvas.Canvas, title: str, y: float) -> float:
    y = _handle_page_break(pdf_canvas, y, 0.8 * cm)
    pdf_canvas.setFillColor(colors.HexColor('#15253e'))
    pdf_canvas.roundRect(MARGIN, y - 0.7 * cm, PAGE_WIDTH - 2 * MARGIN, 0.7 * cm, 6, fill=1, stroke=0)
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.setFont('DejaVu-Bold', 11)
    pdf_canvas.drawString(MARGIN + 0.25 * cm, y - 0.48 * cm, title)
    return y - 1.0 * cm


def _estimate_card_height(pdf_canvas: canvas.Canvas, text: str, width: float) -> float:
    paragraph = Paragraph(text, TEXT_STYLE)
    _, height = paragraph.wrapOn(pdf_canvas, width, 1000)
    return height + 0.4 * cm


def _draw_page_header_footer(pdf_canvas: canvas.Canvas) -> None:
    header_y = PAGE_HEIGHT - MARGIN - 0.45 * cm
    pdf_canvas.setFillColor(colors.HexColor('#14284a'))
    pdf_canvas.roundRect(MARGIN, header_y, PAGE_WIDTH - 2 * MARGIN, 0.5 * cm, 6, fill=1, stroke=0)
    pdf_canvas.setFillColor(colors.white)
    pdf_canvas.setFont('DejaVu-Bold', 8)
    pdf_canvas.drawString(MARGIN + 0.25 * cm, header_y + 0.12 * cm, 'Groww Portfolio Intelligence')
    
    # REMOVED: drawRightString for page numbers. The custom canvas handles it now.

    footer_y = MARGIN - 0.25 * cm
    pdf_canvas.setFillColor(colors.HexColor('#e8edf7'))
    pdf_canvas.roundRect(MARGIN, footer_y, PAGE_WIDTH - 2 * MARGIN, 0.45 * cm, 6, fill=1, stroke=0)
    pdf_canvas.setFillColor(colors.HexColor('#24364f'))
    pdf_canvas.setFont('DejaVu', 7.5)
    
    # Grab data directly from the canvas attributes we set earlier
    report_id = getattr(pdf_canvas, 'report_id', 'REPORT-001')
    version = getattr(pdf_canvas, 'report_version', 'v1.0')
    
    pdf_canvas.drawString(MARGIN + 0.25 * cm, footer_y + 0.11 * cm, f'Report ID: {report_id} | Version: {version}')
    pdf_canvas.drawRightString(PAGE_WIDTH - MARGIN - 0.25 * cm, footer_y + 0.11 * cm, 'CONFIDENTIAL')

def _draw_progress_bar(pdf_canvas: canvas.Canvas, x: float, y: float, width: float, height: float, label: str, value: Any, color: Any) -> None:
    numeric_value = _coerce_float(value)
    if numeric_value is None:
        numeric_value = 0.0
    numeric_value = max(0.0, min(100.0, numeric_value))

    pdf_canvas.setFillColor(colors.HexColor('#eef3ff'))
    pdf_canvas.roundRect(x, y, width, height, 4, fill=1, stroke=0)
    bar_width = width * (numeric_value / 100.0)
    pdf_canvas.setFillColor(color)
    pdf_canvas.roundRect(x, y, bar_width, height, 4, fill=1, stroke=0)
    pdf_canvas.setFillColor(colors.HexColor('#24364f'))
    pdf_canvas.setFont('DejaVu-Bold', 8)
    pdf_canvas.drawString(x, y + 0.2 * cm, label)
    pdf_canvas.setFont('DejaVu', 8)
    pdf_canvas.drawRightString(x + width, y + 0.2 * cm, f'{numeric_value:.0f}%')



def _build_key_findings(ai_insights: dict, metrics: dict) -> List[str]:
    findings = []
    strengths = ai_insights.get('strengths') or []
    weaknesses = ai_insights.get('weaknesses') or []
    for item in strengths[:3]:
        findings.append(clean_markdown(str(item)))
    for item in weaknesses[:2]:
        findings.append(f'Watch item: {clean_markdown(str(item))}')
    if not findings:
        findings.append(f'Health score is {metrics["health_score_display"]}.')
        findings.append(f'Current risk posture is {metrics["risk_level"]}.')
    return findings[:4]


def _build_list_from_field(value: Any) -> List[str]:
    if isinstance(value, list):
        items = [clean_markdown(str(item)) for item in value if str(item).strip()]
        return items or ['No commentary available.']
    if isinstance(value, dict):
        return [f"{key}: {clean_markdown(str(val))}" for key, val in value.items() if str(val).strip()]
    text = clean_markdown(str(value or '').strip())
    if not text:
        return ['No commentary available.']
    return [text]


def _build_priority_actions(ai_insights: dict, metrics: dict) -> List[str]:
    actions = ai_insights.get('priority_actions') or []
    if isinstance(actions, list) and actions:
        return [clean_markdown(str(item)) for item in actions if str(item).strip()]

    fallback = []
    diversification_score = _coerce_float(metrics.get('diversification_component'))
    if diversification_score is not None and diversification_score < 80.0:
        fallback.append('Increase diversification to reduce concentration risk across holdings and sectors.')

    sector_count = metrics.get('sector_count')
    if sector_count is not None and int(sector_count) <= 3:
        fallback.append('Add exposure across additional sectors to improve resilience and reduce single-theme dependence.')

    largest_holding = metrics.get('largest_holding') or ''
    largest_weight = None
    largest_name = 'the largest position'
    if isinstance(largest_holding, str):
        match = re.search(r'([A-Za-z0-9 .&/-]+)\s*\((\d+(?:\.\d+)?)\s*%\)', largest_holding)
        if match:
            largest_name = match.group(1).strip()
            largest_weight = _coerce_float(match.group(2))
    if largest_weight is not None and largest_weight >= 20.0:
        fallback.append(f'Trim the {largest_name} position and rebalance into complementary holdings.')
    elif metrics.get('holding_count') and int(metrics['holding_count']) >= 5:
        fallback.append('Maintain disciplined rebalancing around the largest holding.')

    if metrics.get('risk_level') not in (None, '-', 'Not available', ''):
        fallback.append('Monitor volatility and rebalance if the risk posture deteriorates.')

    return fallback[:4] or ['Increase diversification to reduce concentration risk across holdings and sectors.']


def _format_investor_profile(value: Any) -> str:
    if isinstance(value, dict):
        sections = []
        profile_type = _safe_text(value.get('type') or value.get('profile_type') or value.get('category'))
        confidence = value.get('confidence')
        reason = _safe_text(value.get('reason') or value.get('summary'))
        if profile_type not in ('Not available', ''):
            sections.append(f"<b>Type:</b> {profile_type}")
        if confidence is not None:
            confidence_value = _coerce_float(confidence)
            if confidence_value is not None:
                if 0.0 < confidence_value <= 1.0:
                    confidence_value *= 100.0
                confidence_display = f'{confidence_value:.0f}%' if confidence_value == int(confidence_value) else f'{confidence_value:.1f}%'
            else:
                confidence_display = f'{confidence}%'
            sections.append(f"<b>Confidence:</b> {confidence_display}")
        if reason not in ('Not available', ''):
            sections.append(f"<b>Reason:</b> {reason}")
        if sections:
            return '<br/>'.join(sections)
    if isinstance(value, (list, tuple)):
        return '<br/>'.join([str(item) for item in value if str(item).strip()]) or 'No investor profile available.'
    text = str(value or '').strip()
    return text or 'No investor profile available.'

def _extract_metrics(report_data: dict) -> dict:
    overview = report_data.get('overview', {}) or {}
    analytics = report_data.get('analytics', {}) or {}
    portfolio_json = analytics.get('portfolio_json', {}) or {}
    risk_metrics = analytics.get('risk_metrics', {}) or {}
    benchmark_metrics = analytics.get('benchmark_metrics', {}) or {}
    health_metrics = analytics.get('health_metrics', {}) or {}
    risk_summary = risk_metrics.get('risk_summary', {}) or {}
    health_summary = health_metrics.get('portfolio_health', {}) or {}
    holdings = list(risk_metrics.get('holdings', []) or [])
    summary = portfolio_json.get('summary', {}) or {}

    invested_value = _coerce_float(summary.get('total_invested_value'))
    current_value = _coerce_float(summary.get('total_live_value'))
    pnl_value = None if current_value is None or invested_value in (None, 0) else current_value - invested_value
    return_pct = None if current_value is None or invested_value in (None, 0) else ((current_value - invested_value) / invested_value) * 100

    health_score = _coerce_float(health_summary.get('overall_score'))
    risk_score = _coerce_float(risk_summary.get('risk_score'))
    risk_level = risk_summary.get('risk_level') or risk_summary.get('risk_level_name') or overview.get('Risk Score') or '-'
    portfolio_beta = _coerce_float(risk_summary.get('portfolio_beta'))
    volatility = _coerce_float(risk_summary.get('volatility', {}).get('value_pct'))
    if volatility is None:
        volatility = _coerce_float(risk_summary.get('volatility'))
    drawdown = _coerce_float(risk_summary.get('max_drawdown', {}).get('percent'))
    sharpe = _coerce_float(risk_summary.get('sharpe_ratio'))
    diversification_score = _coerce_float(risk_summary.get('diversification_score'))
    if diversification_score is None:
        diversification_score = _coerce_float(risk_metrics.get('diversification', {}).get('score'))
    benchmark_name = benchmark_metrics.get('benchmark_name') or benchmark_metrics.get('benchmark') or overview.get('Benchmark') or '-'
    benchmark_return = _coerce_float(benchmark_metrics.get('benchmark_return_pct'))
    portfolio_return = _coerce_float(benchmark_metrics.get('portfolio_weighted_return_pct'))
    if portfolio_return is None:
        portfolio_return = _coerce_float(benchmark_metrics.get('portfolio_weighted_return_pct'))
    alpha_value = _coerce_float(benchmark_metrics.get('alpha_pct'))
    tracking_error = _coerce_float(benchmark_metrics.get('tracking_error_pct'))
    information_ratio = _coerce_float(benchmark_metrics.get('information_ratio'))
    relative_performance = _coerce_float(benchmark_metrics.get('portfolio_relative_performance_pct'))
    benchmark_rating = _classify_benchmark_rating(relative_performance)

    sector_counts: dict = {}
    for holding in holdings:
        sector = holding.get('sector') or 'Unassigned'
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    sector_count = len(sector_counts)

    largest_holding = '-'
    largest_weight = None
    for holding in holdings:
        weight = _coerce_float(holding.get('weight_pct'))
        if weight is None:
            weight = _coerce_float(holding.get('weight'))
        if weight is None:
            weight = _coerce_float(holding.get('allocation_pct'))
        if weight is None:
            continue
        if largest_weight is None or weight > largest_weight:
            largest_weight = weight
            largest_holding = f"{holding.get('symbol') or holding.get('name') or 'Holding'} ({weight:.1f}%)"
    if largest_holding == '-':
        largest_holding = holdings[0].get('symbol') or holdings[0].get('name') or '-' if holdings else '-'

    largest_sector = max(sector_counts.items(), key=lambda item: item[1], default=('-', 0))[0] if sector_counts else '-'

    holding_allocation = []
    for holding in holdings[:6]:
        weight = _coerce_float(holding.get('weight_pct'))
        if weight is None:
            weight = _coerce_float(holding.get('weight'))
        if weight is None:
            weight = _coerce_float(holding.get('allocation_pct'))
        if weight is None or weight <= 0:
            continue
        holding_allocation.append((holding.get('symbol') or holding.get('name') or 'Holding', float(weight)))
    if not holding_allocation:
        holding_allocation = [('Portfolio', 100.0)]

    sector_allocation = []
    sector_value_map: dict = {}
    for holding in holdings:
        sector = holding.get('sector') or 'Unassigned'
        weight = _coerce_float(holding.get('weight_pct'))
        if weight is None:
            weight = _coerce_float(holding.get('weight'))
        if weight is None:
            weight = _coerce_float(holding.get('allocation_pct'))
        if weight is None:
            continue
        sector_value_map[sector] = sector_value_map.get(sector, 0.0) + float(weight)
    for sector, value in sorted(sector_value_map.items(), key=lambda item: item[1], reverse=True)[:6]:
        sector_allocation.append((sector, value))
    if not sector_allocation:
        sector_allocation = [('Diversified', 100.0)]

    top_holdings = []
    for holding in sorted(holdings, key=lambda item: _coerce_float(item.get('weight_pct')) or _coerce_float(item.get('weight')) or 0.0, reverse=True)[:5]:
        weight = _coerce_float(holding.get('weight_pct'))
        if weight is None:
            weight = _coerce_float(holding.get('weight'))
        if weight is None:
            weight = _coerce_float(holding.get('allocation_pct'))
        if weight is None:
            continue
        top_holdings.append((holding.get('symbol') or holding.get('name') or 'Holding', float(weight)))
    if not top_holdings:
        top_holdings = [('Portfolio', 100.0)]

    sector_exposure = []
    for sector, value in sorted(sector_value_map.items(), key=lambda item: item[1], reverse=True)[:5]:
        sector_exposure.append((sector, value))
    if not sector_exposure:
        sector_exposure = [('Balanced', 100.0)]

    diversification_axes = [
        ('Diversification', diversification_score if diversification_score is not None else 50.0),
        ('Sector Balance', max(0.0, min(100.0, 100.0 - (max((value for _, value in sector_allocation), default=0.0) - 20.0) * 2.0))),
        ('Holding Breadth', min(100.0, len(holdings) * 4.0)),
        ('Correlation', max(0.0, min(100.0, 100.0 - (max(0.0, (risk_score or 0) - 40) * 0.8)))),
        ('Resilience', max(0.0, min(100.0, 100.0 - (drawdown or 0.0) * 1.6))),
    ]

    risk_component = max(0.0, min(100.0, 100.0 - (risk_score or 0.0)))
    performance_component = max(0.0, min(100.0, (return_pct or 0.0) * 2.5 + (health_score or 0.0) / 2.0))
    diversification_component = diversification_score if diversification_score is not None else 0.0
    quality_component = health_score if health_score is not None else 0.0


    return {
        'investor_name': overview.get('Investor Name') or portfolio_json.get('client_name') or '-',
        'investment_amount_display': _format_currency(invested_value),
        'current_value_display': _format_currency(current_value),
        'pnl_display': _format_currency(pnl_value),
        'return_display': _format_percent(return_pct),
        'health_score_display': _format_percent(health_score),
        'health_score_value': health_score if health_score is not None else 0.0,
        'health_grade': health_summary.get('grade') or health_summary.get('status') or '-',
        'risk_score_display': _format_percent(risk_score),
        'risk_score_value': risk_score if risk_score is not None else 0.0,
        'risk_level': str(risk_level or '-'),
        'benchmark_name': benchmark_name,
        'holding_count': len(holdings),
        'sector_count': sector_count,
        'largest_holding': largest_holding,
        'largest_sector': largest_sector,
        'portfolio_beta_display': _format_number(portfolio_beta),
        'volatility_display': _format_percent(volatility),
        'drawdown_display': _format_percent(drawdown),
        'sharpe_display': _format_number(sharpe),
        'diversification_display': _format_percent(diversification_score),
        'benchmark_performance_display': _format_percent(benchmark_return),
        'portfolio_performance_display': _format_percent(portfolio_return),
        'benchmark_rating': benchmark_rating,
        'holding_allocation': holding_allocation,
        'sector_allocation': sector_allocation,
        'top_holdings': top_holdings,
        'sector_exposure': sector_exposure,
        'diversification_axes': diversification_axes,
        'current_value': current_value,
        'return_value': return_pct,
        'portfolio_return_value': portfolio_return,
        'benchmark_return_value': benchmark_return,
        'risk_component': risk_component,
        'performance_component': performance_component,
        'diversification_component': diversification_component,
        'quality_component': quality_component,
        'alpha_display': _format_percent(alpha_value),
        'tracking_error_display': _format_percent(tracking_error),
        'information_ratio_display': _format_number(information_ratio),
    }


def _classify_benchmark_rating(relative_performance: Optional[float]) -> str:
    if relative_performance is None:
        return '-'
    if relative_performance > 0:
        return 'Outperforming'
    if relative_performance < 0:
        return 'Underperforming'
    return 'In Line'


def _join_values(values: List[Any]) -> str:
    if not values:
        return 'Not available'
    return ', '.join([str(value) for value in values if str(value).strip()])


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        cleaned = cleaned.replace(',', '').replace('₹', '')
        if cleaned.endswith('%'):
            cleaned = cleaned[:-1]
        try:
            return float(cleaned)
        except ValueError:
            match = re.search(r'-?\d+(?:\.\d+)?', cleaned)
            if match:
                return float(match.group(0))
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_text(value: Any) -> str:
    if value is None:
        return 'Not available'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list, tuple)):
        return 'Not available'
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or 'Not available'
    return str(value)
def clean_markdown(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    return text.strip()

def _format_currency(value: Any) -> str:
    numeric_value = _coerce_float(value)
    if numeric_value is None:
        return '-'
    return f'₹ {numeric_value:,.0f}'


def _format_percent(value: Any) -> str:
    numeric_value = _coerce_float(value)
    if numeric_value is None:
        return '-'
    return f'{numeric_value:.2f}%'


def _format_number(value: Any) -> str:
    numeric_value = _coerce_float(value)
    if numeric_value is None:
        return '-'
    return f'{numeric_value:.2f}'
