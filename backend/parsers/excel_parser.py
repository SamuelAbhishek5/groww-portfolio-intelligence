# backend/parsers/excel_parser.py

from pathlib import Path
from typing import Dict, List, Any

import pandas as pd


class GrowwExcelParser:
    """
    Parser for Groww Stock Holdings Excel Statements
    """

    HEADER_ROW = 10

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse Groww holdings excel file

        Returns:
        {
            "client_name": "...",
            "client_code": "...",
            "summary": {...},
            "holdings": [...]
        }
        """

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"{file_path} not found")

        raw_df = pd.read_excel(file_path, header=None)

        client_name = self._extract_client_name(raw_df)
        client_code = self._extract_client_code(raw_df)

        summary = self._extract_summary(raw_df)

        holdings = self._extract_holdings(file_path)

        return {
            "client_name": client_name,
            "client_code": client_code,
            "summary": summary,
            "holdings": holdings,
        }

    def _extract_client_name(self, df: pd.DataFrame) -> str:
        try:
            return str(df.iloc[0, 1]).strip()
        except Exception:
            return ""

    def _extract_client_code(self, df: pd.DataFrame) -> str:
        try:
            return str(df.iloc[1, 1]).strip()
        except Exception:
            return ""

    def _extract_summary(self, df: pd.DataFrame) -> Dict[str, float]:
        return {
            "invested_value": self._safe_float(df.iloc[6, 1]),
            "closing_value": self._safe_float(df.iloc[7, 1]),
            "unrealised_pnl": self._safe_float(df.iloc[8, 1]),
        }

    def _extract_holdings(self, file_path: Path) -> List[Dict]:

        holdings_df = pd.read_excel(
            file_path,
            header=self.HEADER_ROW
        )

        holdings_df.columns = (
            holdings_df.columns
            .astype(str)
            .str.strip()
        )

        holdings_df = holdings_df.dropna(
            how="all"
        ).reset_index(drop=True)

        holdings = []

        for _, row in holdings_df.iterrows():

            stock_name = row.get("Stock Name")

            if pd.isna(stock_name):
                continue

            holdings.append(
                {
                    "stock_name": str(stock_name).strip(),
                    "isin": self._safe_str(row.get("ISIN")),
                    "quantity": self._safe_float(
                        row.get("Quantity")
                    ),
                    "average_buy_price": self._safe_float(
                        row.get("Average buy price")
                    ),
                    "buy_value": self._safe_float(
                        row.get("Buy value")
                    ),
                    "closing_price": self._safe_float(
                        row.get("Closing price")
                    ),
                    "closing_value": self._safe_float(
                        row.get("Closing value")
                    ),
                    "unrealised_pnl": self._safe_float(
                        row.get("Unrealised P&L")
                    ),
                }
            )

        return holdings

    @staticmethod
    def _safe_float(value) -> float:
        try:
            if pd.isna(value):
                return 0.0

            if isinstance(value, str):
                value = value.replace(",", "")

            return float(value)

        except Exception:
            return 0.0

    @staticmethod
    def _safe_str(value) -> str:
        if pd.isna(value):
            return ""

        return str(value).strip()


if __name__ == "__main__":

    parser = GrowwExcelParser()

    result = parser.parse(
        "Stocks_Holdings_Statement_4214763833_2026-06-19.xlsx"
    )

    from pprint import pprint

    pprint(result)