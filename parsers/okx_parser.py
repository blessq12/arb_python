from typing import Dict, List
from .base_parser import BaseExchangeParser
import asyncio


class OkxParser(BaseExchangeParser):
    """Парсер для OKX"""
    
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Получить тикер для пары"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        data = await self.make_request(self.spot_api_url, {
            'instId': normalized_symbol,
        })
        
        if not data.get('data') or not isinstance(data['data'], list) or not data['data']:
            raise Exception('Invalid ticker data format from OKX')
        
        ticker = data['data'][0]
        
        ask = ticker.get('askPx')
        bid = ticker.get('bidPx')
        
        if ask is None or bid is None:
            raise Exception('Missing ask/bid prices in OKX ticker data')
        
        # OKX: vol24h (base) или volCcy24h (в quote)
        volume_24h = None
        if 'volCcy24h' in ticker:
            volume_24h = float(ticker['volCcy24h'])
        elif 'vol24h' in ticker:
            volume_24h = float(ticker['vol24h'])
        
        return {
            'ask': float(ask),
            'bid': float(bid),
            'volume_24h': volume_24h,
        }
    
    async def get_all_symbols(self) -> List[str]:
        """Получить все символы"""
        # OKX публичный список инструментов (SPOT)
        data = await self.make_request('https://www.okx.com/api/v5/public/instruments', {
            'instType': 'SPOT',
        })
        
        if not data.get('data') or not isinstance(data['data'], list):
            raise Exception('Invalid instruments data from OKX')
        
        symbols = []
        for item in data['data']:
            if 'instId' in item:
                symbols.append(item['instId'])
        
        return symbols
    
    async def get_batch_tickers(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """OKX не поддерживает batch, делаем параллельные запросы"""
        tasks = [self.get_ticker(symbol) for symbol in symbols]
        tickers_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for symbol, ticker in zip(symbols, tickers_list):
            if isinstance(ticker, Exception):
                continue
            result[self.normalize_symbol(symbol)] = ticker
        
        return result
    
    def normalize_symbol(self, symbol: str) -> str:
        """OKX использует дефис: BTC/USDT -> BTC-USDT"""
        return symbol.replace('/', '-').upper()
