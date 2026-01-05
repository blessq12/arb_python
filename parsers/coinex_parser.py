from typing import Dict, List
from .base_parser import BaseExchangeParser


class CoinExParser(BaseExchangeParser):
    """Парсер для CoinEx"""
    
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Получить тикер для пары"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        data = await self.make_request(self.spot_api_url, {
            'market': normalized_symbol,
        })
        
        if 'data' not in data or 'ticker' not in data['data']:
            raise Exception('Invalid ticker data format from CoinEx')
        
        ticker = data['data']['ticker']
        
        if 'sell' not in ticker or 'buy' not in ticker:
            raise Exception('Missing ask/bid prices in CoinEx ticker data')
        
        return {
            'ask': float(ticker['sell']),
            'bid': float(ticker['buy']),
            'volume_24h': float(ticker.get('vol', 0)) if ticker.get('vol') else None,
        }
    
    async def get_all_symbols(self) -> List[str]:
        """Получить все символы"""
        data = await self.make_request('https://api.coinex.com/v1/market/info', {})
        
        if 'data' not in data:
            raise Exception('Invalid symbols data format from CoinEx')
        
        symbols = []
        for market, info in data['data'].items():
            if 'name' in info:
                symbols.append(info['name'])
        
        return symbols
    
    def normalize_symbol(self, symbol: str) -> str:
        """CoinEx использует формат без слэша: BTC/USDT -> BTCUSDT"""
        return symbol.replace('/', '').upper()
