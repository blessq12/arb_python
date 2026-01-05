from typing import Dict, List
from .base_parser import BaseExchangeParser


class BybitParser(BaseExchangeParser):
    """Парсер для Bybit"""
    
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Получить тикер для пары"""
        normalized_symbol = self.normalize_symbol(symbol)
        
        data = await self.make_request(self.spot_api_url, {
            'category': 'spot',
            'symbol': normalized_symbol,
        })
        
        if not data.get('result', {}).get('list'):
            raise Exception('Invalid ticker data format from Bybit')
        
        ticker = data['result']['list'][0]
        
        if 'ask1Price' not in ticker or 'bid1Price' not in ticker:
            raise Exception('Missing ask/bid prices in Bybit ticker data')
        
        return {
            'ask': float(ticker['ask1Price']),
            'bid': float(ticker['bid1Price']),
            'volume_24h': float(ticker.get('volume24h', 0)) if ticker.get('volume24h') else None,
        }
    
    async def get_all_symbols(self) -> List[str]:
        """Получить все символы"""
        data = await self.make_request(self.spot_api_url, {
            'category': 'spot',
        })
        
        if not data.get('result', {}).get('list'):
            raise Exception('Invalid symbols data format from Bybit')
        
        symbols = []
        for item in data['result']['list']:
            if 'symbol' in item:
                symbols.append(item['symbol'])
        
        return symbols
    
    async def get_batch_tickers(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Batch запрос для Bybit (поддерживает несколько символов через запятую)"""
        normalized_symbols = [self.normalize_symbol(s) for s in symbols]
        
        # Bybit принимает до 10 символов за раз, разбиваем на батчи
        batch_size = 10
        all_tickers = {}
        
        for i in range(0, len(normalized_symbols), batch_size):
            batch = normalized_symbols[i:i + batch_size]
            
            data = await self.make_request(self.spot_api_url, {
                'category': 'spot',
                'symbol': ','.join(batch),
            })
            
            if not data.get('result', {}).get('list'):
                # Если batch не сработал, делаем индивидуальные запросы для этого батча
                for symbol in batch:
                    try:
                        ticker = await self.get_ticker(symbol)
                        all_tickers[symbol] = ticker
                    except Exception:
                        pass
                continue
            
            for ticker in data['result']['list']:
                if 'symbol' in ticker and 'ask1Price' in ticker and 'bid1Price' in ticker:
                    all_tickers[ticker['symbol']] = {
                        'ask': float(ticker['ask1Price']),
                        'bid': float(ticker['bid1Price']),
                        'volume_24h': float(ticker.get('volume24h', 0)) if ticker.get('volume24h') else None,
                    }
        
        return all_tickers
    
    def normalize_symbol(self, symbol: str) -> str:
        """Bybit использует формат без слэша: BTC/USDT -> BTCUSDT"""
        return symbol.replace('/', '').upper()
