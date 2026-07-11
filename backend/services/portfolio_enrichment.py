# backend/services/portfolio_enrichment.py

from typing import Dict, Any
from backend.market_data.yahoo_client import YahooFinanceClient

# Import your existing parsers
from backend.parsers.excel_parser import GrowwExcelParser
# Uncomment these as you build them:
# from backend.parsers.pdf_parser import GrowwPdfParser
# from backend.parsers.api_parser import GrowwApiParser

class PortfolioEnricher:
    def __init__(self):
        self.yahoo_client = YahooFinanceClient()

    def _get_parser(self, source_type: str):
        """
        Dynamically returns the correct parser based on the source type.
        """
        source_type = source_type.lower().strip()
        
        if source_type == 'excel':
            return GrowwExcelParser()
        # elif source_type == 'pdf':
        #     return GrowwPdfParser()
        # elif source_type == 'api':
        #     return GrowwApiParser()
        else:
            raise ValueError(f"Unsupported source type: '{source_type}'. Choose from 'excel', 'pdf', or 'api'.")

    def process_portfolio(self, source_type: str, source_data: Any) -> Dict:
        """
        Parses the portfolio using the requested parser and enriches it with Yahoo Finance data.
        """
        # 1. Initialize the correct parser and extract raw data
        parser = self._get_parser(source_type)
        
        # Assuming all your parsers have a unified method, like `.parse(source_data)`
        # You may need to adjust this depending on how your parsers are structured.
        raw_portfolio = parser.parse(source_data) 
        
        enriched_holdings = []
        total_invested = 0.0
        total_live_value = 0.0

        # 2. Iterate through holdings and merge market data
        for item in raw_portfolio.get('holdings', []):
            # Clean the ISIN (Removing curly/smart quotes like '“INE002A01018”')
            raw_isin = item.get('isin', '')
            clean_isin = raw_isin.strip('“"”\' ')
            
            # Fetch data from YahooClient
            market_info = self.yahoo_client.get_stock_info(clean_isin)
            live_price = self.yahoo_client.get_current_price(clean_isin)

            # Create a new merged dictionary
            enriched_item = {
                **item,                 # Unpack all original Excel/PDF data
                'isin': clean_isin,     # Overwrite with clean ISIN
            }

            # If Yahoo found the stock info, merge it in
            if market_info:
                enriched_item.update({
                    'symbol': market_info.get('symbol'),
                    'sector': market_info.get('sector'),
                    'industry': market_info.get('industry'),
                    'market_cap': market_info.get('market_cap'),
                    'pe_ratio': market_info.get('pe_ratio'),
                    'dividend_yield': market_info.get('dividend_yield')
                })

            # If Yahoo found the live price, calculate live metrics
            if live_price:
                quantity = item.get('quantity', 0)
                buy_value = item.get('buy_value', 0)
                
                current_value = live_price * quantity
                
                enriched_item['live_price'] = live_price
                enriched_item['live_value'] = current_value
                enriched_item['live_unrealised_pnl'] = current_value - buy_value
                
                total_invested += buy_value
                total_live_value += current_value

            enriched_holdings.append(enriched_item)

        # 3. Recalculate the summary section based on live data
        # (This fixes the 0.0 values from your raw Excel output)
        enriched_summary = {
            'total_invested_value': total_invested,
            'total_live_value': total_live_value,
            'total_unrealised_pnl': total_live_value - total_invested
        }

        # 4. Return the final unified JSON structure
        return {
            'client_code': raw_portfolio.get('client_code'),
            'client_name': raw_portfolio.get('client_name'),
            'summary': enriched_summary,
            'holdings': enriched_holdings
        }

if __name__ == "__main__":
    # Example usage:
    enricher = PortfolioEnricher()
    
    # Simulating passing an excel file path
    file_path = "Stocks_Holdings_Statement_4214763833_2026-06-19.xlsx"
    
    try:
        final_json = enricher.process_portfolio(source_type="excel", source_data=file_path)
        
        import json
        print(json.dumps(final_json, indent=4))
        
    except Exception as e:
        print(f"Error processing portfolio: {e}")