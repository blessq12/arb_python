from typing import Dict, List
from .base_parser import BaseExchangeParser


class HtxParser(BaseExchangeParser):
    """Парсер для HTX (Huobi)"""
    
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Получить тикер для пары"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        data = await self.make_request(self.spot_api_url, {
            'symbol': normalized_symbol,
        })
        
        if 'tick' not in data:
            raise Exception('Invalid ticker data format from HTX')
        
        tick = data['tick']
        
        if 'close' not in tick:
            raise Exception('Missing price data in HTX ticker')
        
        close = float(tick['close'])
        volume24h = tick.get('amount') or tick.get('vol')
        
        # HTX не возвращает ask/bid в merged, используем close как приближение
        return {
            'ask': close,
            'bid': close,
            'volume_24h': float(volume24h) if volume24h else None,
        }
    
    async def get_all_symbols(self) -> List[str]:
        """Получить все символы"""
        data = await self.make_request('https://api.huobi.pro/v1/common/symbols', {})
        
        if 'data' not in data or not isinstance(data['data'], list):
            raise Exception('Invalid symbols data from HTX')
        
        symbols = []
        for item in data['data']:
            if (item.get('base-currency') and item.get('quote-currency') and 
                item.get('state') == 'online'):
                symbols.append((item['base-currency'] + item['quote-currency']).upper())
        
        return symbols
    
    def normalize_symbol(self, symbol: str) -> str:
        """HTX: нижний регистр без разделителей: BTC/USDT -> btcusdt"""
        return symbol.replace('/', '').lower()
    
    def normalize_interval(self, interval: str) -> str:
        """HTX интервалы"""
        mapping = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '30m': '30min',
            '1h': '60min',
            '4h': '4hour',
            '1d': '1day',
        }
        if interval not in mapping:
            raise Exception(f"Unsupported interval for HTX: {interval}")
        return mapping[interval]
