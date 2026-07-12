# 📈 Groww Portfolio Intelligence

Groww Portfolio Intelligence is an AI-powered portfolio analysis platform that transforms a user's Groww portfolio into a comprehensive investment report. It combines financial analytics, risk assessment, benchmark comparison, portfolio health evaluation, and AI-generated insights to help investors better understand their portfolios.

Built using FastAPI, Python, JavaScript, financial analytics, and Gemini AI.

---

# What It Does

Managing an investment portfolio can be challenging, especially for individual investors who often rely only on basic metrics such as current value and profit/loss. Understanding the overall health of a portfolio, identifying hidden risks, measuring diversification, comparing performance with market benchmarks, and determining areas for improvement requires significant financial analysis that is not readily available to most users.

Groww Portfolio Intelligence was built to simplify this process by providing a comprehensive analysis of a user’s investment portfolio. The platform processes a Groww portfolio export and evaluates key financial metrics, including portfolio risk, diversification, sector allocation, benchmark performance, and overall portfolio health.

In addition to quantitative analysis, the platform uses AI to generate easy-to-understand insights and practical tips about the portfolio. These insights help users recognize the strengths and weaknesses of their investments, understand potential risks, and identify opportunities to improve diversification and long-term portfolio performance.

Finally, all analyses, insights, and recommendations are compiled into a professional PDF report and an interactive dashboard, enabling users to better understand their portfolio and make more informed investment decisions.

---

# Features

- 📂 Upload Groww portfolio files
- 📊 Portfolio summary and holdings analysis
- 📈 Portfolio risk analysis
- 📉 Volatility and Beta calculation
- ⚖️ Value at Risk (VaR) estimation
- 📌 Concentration risk detection
- 🌐 Sector allocation analysis
- 🔄 Diversification analysis
- 🏥 Portfolio Health Score
- 📈 Benchmark comparison against NIFTY 50
- 💡 Opportunity detection and recommendations
- 🤖 AI-generated portfolio insights using Gemini
- 📄 Professional PDF report generation
- ⚡ Interactive dashboard
- 🔗 REST API powered by FastAPI

---

# Analytics Modules

### Portfolio Analytics
- Portfolio valuation
- Unrealized Profit & Loss
- Asset allocation
- Holding summary

### Risk Engine
- Portfolio Beta
- Annualized Volatility
- Value at Risk (VaR)
- Expected Shortfall
- Maximum Drawdown
- Sharpe Ratio
- Concentration Risk

### Portfolio Health Engine
- Overall Health Score
- Risk Score
- Diversification Score
- Performance Score
- Stability Score
- Quality Score

### Benchmark Engine
- Portfolio Return
- NIFTY 50 Comparison
- Alpha
- Relative Performance
- Information Ratio
- Tracking Error

### Opportunity Engine
- Sector exposure analysis
- Diversification recommendations
- Concentration alerts
- Portfolio improvement suggestions

### AI Insight Engine
- Personalized portfolio summary
- Risk explanation
- Strength identification
- Weakness analysis
- Actionable recommendations
- Natural language investment insights

---

# System Architecture

```
                        User

                          │

                          ▼

                HTML • CSS • JavaScript

                          │

                          ▼

                   FastAPI Backend

          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼

     Excel Parser   Analytics Engine   AI Engine
                        │               (Gemini)

          ┌──────────────┼──────────────┐
          ▼              ▼              ▼

      Risk Engine   Health Engine   Benchmark Engine

                          │

                          ▼

                  Opportunity Engine

                          │

                          ▼

                  PDF Report Generator

                          │

                          ▼

              Interactive Dashboard + Report
```

---

# Tech Stack

## Frontend

- HTML5
- CSS3
- JavaScript

## Backend

- FastAPI
- Python

## Financial Analytics

- Pandas
- NumPy
- yFinance

## AI

- Gemini API

## Reporting

- ReportLab

## Deployment

- Render

---

# Installation

Clone the repository

```bash
https://github.com/SamuelAbhishek5/groww-portfolio-intelligence.git
```

Move into the project

```bash
cd groww-portfolio-intelligence
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run the application

```bash
uvicorn app:app --reload
```

Open

```
http://127.0.0.1:8000
```

---

# Usage

1. Upload your Groww portfolio Excel file report.
2. Portfolio data is parsed automatically.
3. Financial metrics are calculated.
4. AI generates portfolio insights.
5. A dashboard displays the analysis.
6. Download the generated PDF report.

---

# API Documentation


Application

```
https://groww-portfolio-intelligence.onrender.com/
```

---

# Project Structure

```
Groww-Portfolio-Intelligence/

│── backend/
│── frontend/
│── tests/
│── requirements.txt
│── README.md
│── LICENSE
```

---

# Screenshots

### Home Page

<img width="1438" height="781" alt="Screenshot 2026-07-12 at 12 04 14 PM" src="https://github.com/user-attachments/assets/48d80942-4efc-4b81-841d-b41356e22003" />


### Processing Page

<img width="1432" height="782" alt="Screenshot 2026-07-12 at 12 06 13 PM" src="https://github.com/user-attachments/assets/deef23b3-29b1-4a25-90cd-b55c6138490e" />


### Report Page

<img width="1357" height="684" alt="Screenshot 2026-07-12 at 12 08 20 PM" src="https://github.com/user-attachments/assets/5b48d852-939f-4d87-b59c-a9ad8162c92f" />


### PDF Report

<img width="1429" height="783" alt="Screenshot 2026-07-12 at 12 09 05 PM" src="https://github.com/user-attachments/assets/89ec440a-34b4-4e59-801f-6497860f0746" />

### Follow Up Chatbot

<img width="1355" height="537" alt="Screenshot 2026-07-12 at 12 08 46 PM" src="https://github.com/user-attachments/assets/61ca0f5b-7000-4f3e-bcd7-4e362fb98f84" />


---

# Future Enhancements

- Multi-user authentication
- Groww API parser
- Portfolio tracking over time
- Mutual fund support
- ETF analysis
- Stock price forecasting
- Portfolio optimization suggestions
- Email report delivery
- Mobile-responsive dashboard
- Real-time market updates
- Multi-language support

---

# Requirements

- Python 3.11+
- FastAPI
- Internet connection (for market data and AI insights)
- Gemini API Key

---


# Disclaimer

This project is intended for educational and informational purposes only.

The generated analysis and AI insights should not be considered financial or investment advice. Users should conduct their own research or consult a qualified financial advisor before making investment decisions.

Market data is obtained from publicly available sources, and while every effort is made to ensure accuracy, no guarantees are provided regarding completeness or correctness.

---

# Author

**Abhishek M**

B.Tech – Data Science

GitHub: https://github.com/SamuelAbhishek5

LinkedIn: https://www.linkedin.com/in/abhishek-m-99368425b/
