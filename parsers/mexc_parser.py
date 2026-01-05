from typing import Dict, List
from .base_parser import BaseExchangeParser


class MexcParser(BaseExchangeParser):
    """Парсер для MEXC"""
    
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Получить тикер для пары"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        data = await self.make_request(self.spot_api_url, {
            'symbol': normalized_symbol,
        })
        
        if 'askPrice' not in data or 'bidPrice' not in data:
            raise Exception('Invalid ticker data format from MEXC')
        
        return {
            'ask': float(data['askPrice']),
            'bid': float(data['bidPrice']),
            'volume_24h': float(data.get('volume', 0)) if data.get('volume') else None,
        }
    
    async def get_all_symbols(self) -> List[str]:
        """Получить все символы"""
        data = await self.make_request('https://api.mexc.com/api/v3/exchangeInfo', {})
        
        if 'symbols' not in data:
            raise Exception('Invalid symbols data format from MEXC')
        
        symbols = []
        for symbol_data in data['symbols']:
            if symbol_data.get('symbol') and symbol_data.get('status') == 'TRADING':
                symbols.append(symbol_data['symbol'])
        
        return symbols
    
    def normalize_symbol(self, symbol: str) -> str:
        """MEXC использует формат без слэша: BTC/USDT -> BTCUSDT"""
        return symbol.replace('/', '').upper()
