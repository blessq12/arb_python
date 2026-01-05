from typing import Dict, List
from .base_parser import BaseExchangeParser


class PoloniexParser(BaseExchangeParser):
    """Парсер для Poloniex"""
    
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Получить тикер для пары"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        # Poloniex использует прямой URL для тикера
        url = f"https://api.poloniex.com/markets/{normalized_symbol}/ticker24h"
        data = await self.make_request(url, {})
        
        if 'close' not in data:
            raise Exception('Invalid ticker data from Poloniex')
        
        close = float(data['close'])
        volume24h = data.get('amount')
        
        # Используем close как ask/bid (Poloniex не предоставляет отдельные ask/bid в этом endpoint)
        return {
            'ask': close,
            'bid': close,
            'volume_24h': float(volume24h) if volume24h else None,
        }
    
    async def get_all_symbols(self) -> List[str]:
        """Получить все символы"""
        data = await self.make_request('https://api.poloniex.com/markets', {})
        
        if not isinstance(data, list):
            raise Exception('Invalid symbols data from Poloniex')
        
        symbols = []
        for item in data:
            if (item.get('state', 'NORMAL') == 'NORMAL' and item.get('symbol')):
                symbols.append(item['symbol'])
        
        return symbols
    
    def normalize_symbol(self, symbol: str) -> str:
        """Poloniex использует нижнее подчеркивание: BTC/USDT -> BTC_USDT"""
        return symbol.replace('/', '_').upper()
