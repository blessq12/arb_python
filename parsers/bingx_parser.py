from typing import Dict, List
import time
from .base_parser import BaseExchangeParser


class BingXParser(BaseExchangeParser):
    """Парсер для BingX"""
    
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Получить тикер для пары"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        data = await self.make_request(self.spot_api_url, {
            'symbol': normalized_symbol,
            'timestamp': int(time.time() * 1000),  # BingX требует timestamp в миллисекундах
        })
        
        if 'data' not in data or not isinstance(data['data'], list):
            raise Exception('Invalid ticker data format from BingX')
        
        ticker = data['data'][0] if isinstance(data['data'], list) else data['data']
        
        if 'askPrice' not in ticker or 'bidPrice' not in ticker:
            raise Exception('Missing ask/bid prices in BingX ticker data')
        
        return {
            'ask': float(ticker['askPrice']),
            'bid': float(ticker['bidPrice']),
            'volume_24h': float(ticker.get('quoteVolume', 0)) if ticker.get('quoteVolume') else None,
        }
    
    async def get_all_symbols(self) -> List[str]:
        """Получить все символы (BingX не имеет простого endpoint)"""
        return []
    
    def normalize_symbol(self, symbol: str) -> str:
        """BingX использует формат с дефисом: BTC/USDT -> BTC-USDT"""
        return symbol.replace('/', '-').upper()
