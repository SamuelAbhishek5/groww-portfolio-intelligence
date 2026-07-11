import pandas as pd
import plotly.express as px

from backend.analytics.benchmark_engine import BenchmarkEngine


class PortfolioReporter:
    def __init__(self, portfolio_data: dict):
        self.portfolio = portfolio_data
        self.summary = portfolio_data.get("summary", {})
        self.holdings = portfolio_data.get("holdings", [])
        self.df = pd.DataFrame(self.holdings)
        self.benchmark_engine = BenchmarkEngine()

        # 1. DASHBOARD METRICS
    def get_dashboard_metrics(self):
        invested = self.summary.get("total_invested_value", 0)
        current = self.summary.get("total_live_value", 0)
        pnl = self.summary.get("total_unrealised_pnl", 0)
        return_pct = (pnl / invested) * 100 if invested > 0 else 0
        return {
            "investment": invested,
            "current_value": current,
            "profit": pnl,
            "return_pct": round(return_pct, 2),
        }

    def print_dashboard_metrics(self):
        metrics = self.get_dashboard_metrics()
        benchmark_result = self.benchmark_engine.compare_portfolio(self.portfolio)

        print("\n========== PORTFOLIO SUMMARY ==========")
        print(f"Investment             ₹{metrics['investment']:,.0f}")
        print(f"Current Value          ₹{metrics['current_value']:,.0f}")
        print(f"Profit                 ₹{metrics['profit']:,.0f}")
        sign = "+" if metrics["return_pct"] > 0 else ""
        print(f"Investment Return      {sign}{metrics['return_pct']:.2f}%")
        print("=======================================")

        print("\n========== BENCHMARK REPORT ==========")

        if benchmark_result.get("error"):
            print(f"Error                  {benchmark_result['error']}")
            print("=======================================\n")
            return

        benchmark_name = benchmark_result.get("benchmark_name") or benchmark_result.get("benchmark")

        print(f"Benchmark              {benchmark_name}")
        print(f"Lookback Period        {benchmark_result.get('lookback_period', 'N/A')}")
        print(f"Benchmark Return       {benchmark_result['benchmark_return_pct']:.2f}%")
        print(f"Weighted Holdings Return {benchmark_result['portfolio_weighted_return_pct']:.2f}%")
        print(f"Relative Performance  {benchmark_result['portfolio_relative_performance_pct']:.2f}%")
        print(f"Portfolio Rating      {benchmark_result.get('overall_rating', 'N/A')}")
        print(f"Outperforming Holdings {benchmark_result['outperforming_holdings']} / {len(benchmark_result.get('holdings', []))}")

        coverage = benchmark_result.get("coverage", {})
        if coverage:
            print(
                f"Coverage              {coverage.get('analysed_holdings', 0)} / "
                f"{coverage.get('total_holdings', 0)} ({coverage.get('coverage_pct', 0):.1f}%)"
            )

        print("---------------------------------------")
        print(f"Strongest Holding     {benchmark_result.get('strongest_stock', 'N/A')}")
        print(f"Weakest Holding       {benchmark_result.get('weakest_stock', 'N/A')}")
        print("---------------------------------------")

        print(f"{'Rank':<5} {'Stock':<28} {'Return':>10} {'Relative':>12} {'Class':>18}")

        for holding in benchmark_result.get("holdings", []):
            print(
                f"{holding.get('rank', '-'):>4} "
                f"{holding.get('stock_name', holding.get('symbol', 'N/A')):<28.28} "
                f"{holding.get('stock_return_pct', 0):>9.2f}% "
                f"{holding.get('relative_performance_pct', 0):>11.2f}% "
                f"{holding.get('classification', 'N/A'):>18}"
            )

        print("=======================================\n")

        # 2. ASSET ALLOCATION
    def get_asset_allocation(self):
        current_value = self.summary.get("total_live_value", 0)
        allocation = {"Stocks": current_value, "Cash": 0, "Mutual Funds": 0}
        total = sum(allocation.values())
        return {a: round((v / total) * 100, 2) if total > 0 else 0 for a, v in allocation.items()}

    def print_asset_allocation(self):
        allocation = self.get_asset_allocation()
        print("\n========== ASSET ALLOCATION ==========")
        for asset, pct in allocation.items():
            print(f"{asset:<15} {pct:.2f}%")
        print("\n======================================\n")

        # 3. SECTOR ALLOCATION
    def get_sector_allocation(self):
        if self.df.empty:
            return pd.DataFrame()
        sector_df = self.df.groupby("sector")["live_value"].sum().reset_index()
        total_value = sector_df["live_value"].sum()
        sector_df["allocation_pct"] = (sector_df["live_value"] / total_value) * 100
        return sector_df.sort_values(by="allocation_pct", ascending=False)

    def print_sector_allocation(self):
        sector_df = self.get_sector_allocation()
        print("\n========== SECTOR ALLOCATION ==========")
        for _, row in sector_df.iterrows():
            print(f"{row['sector']:<20} {row['allocation_pct']:.2f}%")
        print("\n=======================================\n")

        # PIE CHART
    def plot_sector_pie_chart(self):
        sector_df = self.get_sector_allocation()
        if sector_df.empty:
            return
        fig = px.pie(sector_df, values="live_value", names="sector", title="Portfolio Sector Allocation")
        fig.show()

        # TREEMAP
    def plot_sector_treemap(self):
        if self.df.empty:
            return
        fig = px.treemap(self.df, path=[px.Constant("Portfolio"), "sector", "stock_name"], values="live_value", title="Portfolio Treemap")
        fig.show()

        # COMPLETE MODULE 3
    def generate_report(self):
        self.print_dashboard_metrics()
        self.print_asset_allocation()
        self.print_sector_allocation()
        self.plot_sector_pie_chart()
        self.plot_sector_treemap()