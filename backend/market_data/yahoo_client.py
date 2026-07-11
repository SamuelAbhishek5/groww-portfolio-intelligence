# backend/market_data/yahoo_client.py

from typing import Dict, List, Optional
import requests
import pandas as pd
import yfinance as yf


class YahooFinanceClient:

    def __init__(self):
        # Using a standard user-agent so Yahoo doesn't block the search request
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def _get_symbol_from_isin(self, isin: str) -> Optional[str]:
        """
        Translates an ISIN to a Yahoo Finance ticker symbol using Yahoo's search API.
        Example: INE009A01021 -> INFY.NS
        """
        isin = isin.strip().upper()
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            quotes = data.get('quotes', [])
            if quotes:
                # Return the first matching symbol found
                return quotes[0].get('symbol')
                
            print(f"No symbol found for ISIN: {isin}")
            return None
            
        except Exception as e:
            print(f"Error resolving ISIN {isin}: {e}")
            return None

    def get_stock_info(self, isin: str) -> Dict:
        """
        Get stock metadata using ISIN.
        """
        symbol = self._get_symbol_from_isin(isin)
        if not symbol:
            return {}

        ticker = yf.Ticker(symbol)

        try:
            info = ticker.info

            return {
                "isin": isin,
                "symbol": symbol,
                "company_name": info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "beta": info.get("beta"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "roe": info.get("returnOnEquity"),
                "dividend_yield": info.get("dividendYield"),
                "currency": info.get("currency"),
            }

        except Exception as e:
            print(f"Error fetching info for ISIN {isin} (Resolved to {symbol}): {e}")
            return {}

    def get_current_price(self, isin: str) -> Optional[float]:
        """
        Get latest market price using ISIN.
        """
        symbol = self._get_symbol_from_isin(isin)
        if not symbol:
            return None

        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period="1d")

            if history.empty:
                return None

            return float(history["Close"].iloc[-1])

        except Exception as e:
            print(f"Price fetch error for ISIN {isin} (Resolved to {symbol}): {e}")
            return None

    def get_historical_prices(
        self,
        symbol: Optional[str] = None,
        period: str = "2y",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        isin: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Historical OHLC data for either a direct ticker symbol or an ISIN.
        """
        symbol_or_isin = symbol or isin
        if not symbol_or_isin:
            return pd.DataFrame()

        query_symbol = symbol_or_isin
        try:
            ticker = yf.Ticker(query_symbol)
            history = ticker.history(period=period, start=start_date, end=end_date)
            if not history.empty:
                return history.reset_index()
        except Exception as e:
            print(f"Historical data error for {query_symbol}: {e}")

        if symbol_or_isin and len(str(symbol_or_isin)) > 6 and not str(symbol_or_isin).startswith("^"):
            resolved_symbol = self._get_symbol_from_isin(symbol_or_isin)
            if resolved_symbol:
                try:
                    ticker = yf.Ticker(resolved_symbol)
                    history = ticker.history(period=period, start=start_date, end=end_date)
                    if not history.empty:
                        return history.reset_index()
                except Exception as e:
                    print(f"Historical data error for {symbol_or_isin} (Resolved to {resolved_symbol}): {e}")

        return pd.DataFrame()

    def get_daily_returns(self, isin: str, period: str = "2y") -> pd.Series:
        """
        Daily percentage returns using ISIN.
        """
        prices = self.get_historical_prices(isin=isin, period=period)

        if prices.empty:
            return pd.Series(dtype=float)

        prices["returns"] = prices["Close"].pct_change()
        return prices["returns"].dropna()

    def get_bulk_stock_info(self, isins: List[str]) -> Dict[str, Dict]:
        """
        Fetch info for multiple stocks using ISINs.
        """
        results = {}
        for isin in isins:
            results[isin] = self.get_stock_info(isin)
        return results

    def get_bulk_current_prices(self, isins: List[str]) -> Dict[str, float]:
        """
        Fetch current prices for multiple stocks using ISINs.
        """
        results = {}
        for isin in isins:
            results[isin] = self.get_current_price(isin)
        return results


if __name__ == "__main__":
    yahoo = YahooFinanceClient()

    # Using Infosys ISIN as an example
    test_isin = "INE002A01018" 

    print(f"--- Testing Data Fetch for ISIN: {test_isin} ---")
    
    info = yahoo.get_stock_info(test_isin)
    print("\nStock Info:")
    import json
    print(json.dumps(info, indent=4))

    current_price = yahoo.get_current_price(test_isin)
    print(f"\nCurrent Price: {current_price}")

    history = yahoo.get_historical_prices(test_isin)
    print("\nHistorical Data (Head):")
    print(history.head())