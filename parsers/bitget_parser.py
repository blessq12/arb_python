from typing import Dict, List
import asyncio
from .base_parser import BaseExchangeParser


class BitgetParser(BaseExchangeParser):
    """Парсер для Bitget"""
    
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Получить тикер для пары"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        data = await self.make_request(self.spot_api_url, {
            'symbol': normalized_symbol,
        })
        
        if 'data' not in data:
            raise Exception('Invalid ticker data format from Bitget')
        
        item = data['data'][0] if isinstance(data['data'], list) else data['data']
        
        ask = item.get('sellOne') or item.get('bestAsk') or item.get('askPx')
        bid = item.get('buyOne') or item.get('bestBid') or item.get('bidPx')
        
        if ask is None or bid is None:
            raise Exception('Missing ask/bid in Bitget ticker')
        
        volume24h = item.get('quoteVol') or item.get('baseVol')
        
        return {
            'ask': float(ask),
            'bid': float(bid),
            'volume_24h': float(volume24h) if volume24h else None,
        }
    
    async def get_all_symbols(self) -> List[str]:
        """Получить все символы"""
        data = await self.make_request('https://api.bitget.com/api/spot/v1/public/products', {})
        
        if 'data' not in data or not isinstance(data['data'], list):
            raise Exception('Invalid symbols data from Bitget')
        
        symbols = []
        for item in data['data']:
            if (item.get('status', 'online') == 'online' and item.get('symbol')):
                symbols.append(item['symbol'])
        
        return symbols
    
    async def get_batch_tickers(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Bitget единичный эндпоинт, делаем параллельные запросы"""
        tasks = [self.get_ticker(symbol) for symbol in symbols]
        tickers_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for symbol, ticker in zip(symbols, tickers_list):
            if isinstance(ticker, Exception):
                continue
            result[self.normalize_symbol(symbol)] = ticker
        
        return result
    
    def normalize_symbol(self, symbol: str) -> str:
        """Bitget использует формат с дефисом: BTC/USDT -> BTC-USDT"""
        return symbol.replace('/', '-').upper()
    
    def normalize_interval(self, interval: str) -> str:
        """Bitget интервалы"""
        mapping = {
            '1m': '1min',
            '5m': '5min',
            '15m': '15min',
            '30m': '30min',
            '1h': '1h',
            '4h': '4h',
            '1d': '1day',
        }
        if interval not in mapping:
            raise Exception(f"Unsupported interval for Bitget: {interval}")
        return mapping[interval]
