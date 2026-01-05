import aiohttp
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BaseExchangeParser(ABC):
    """Базовый async парсер биржи"""
    
    def __init__(self, spot_api_url: str, kline_api_url: str, 
                 api_key: Optional[str] = None, api_secret: Optional[str] = None):
        self.spot_api_url = spot_api_url
        self.kline_api_url = kline_api_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Закрыть session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def make_request(self, url: str, params: Optional[Dict] = None, retries: int = 3) -> Dict[str, Any]:
        """Выполнить async HTTP запрос с retry логикой"""
        session = await self._get_session()
        
        for attempt in range(retries):
            try:
                async with session.get(url, params=params or {}) as response:
                    if response.status >= 500 and attempt < retries - 1:
                        wait_time = 2 ** attempt  # экспоненциальная задержка
                        await asyncio.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    data = await response.json()
                    return data
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    continue
                raise Exception(f"Failed to fetch data from exchange after {retries} attempts: {e}")
        
        raise Exception("Request failed after all retries")
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Получить текущие цены ask/bid для пары"""
        pass
    
    @abstractmethod
    async def get_all_symbols(self) -> List[str]:
        """Получить список всех доступных торговых пар"""
        pass
    
    async def get_all_currencies(self) -> List[str]:
        """Получить список всех валют (базовая реализация через символы)"""
        symbols = await self.get_all_symbols()
        currencies = set()
        
        quote_currencies = ['USDT', 'USDC', 'BTC', 'ETH', 'BNB', 'BUSD', 'DAI', 'TUSD', 'PAX', 'USDK']
        
        for symbol in symbols:
            symbol_upper = symbol.upper()
            for quote in quote_currencies:
                if symbol_upper.endswith(quote):
                    base = symbol_upper[:-len(quote)]
                    if base:
                        currencies.add(base)
                        currencies.add(quote)
                        break
            
            # Попытка деления пополам
            if len(symbol_upper) >= 6:
                currencies.add(symbol_upper[:-4])
                currencies.add(symbol_upper[-4:])
        
        return sorted(list(currencies))
    
    async def get_batch_tickers(self, symbols: List[str]) -> Dict[str, Dict[str, float]]:
        """Получить тикеры для нескольких пар (базовая реализация - последовательно)"""
        result = {}
        tasks = [self.get_ticker(symbol) for symbol in symbols]
        tickers = await asyncio.gather(*tasks, return_exceptions=True)
        
        for symbol, ticker in zip(symbols, tickers):
            if isinstance(ticker, Exception):
                logger.warning(f"Error fetching ticker for {symbol}: {ticker}")
            else:
                result[self.normalize_symbol(symbol)] = ticker
        
        return result
    
    @abstractmethod
    def normalize_symbol(self, symbol: str) -> str:
        """Нормализовать символ пары под формат биржи"""
        pass
