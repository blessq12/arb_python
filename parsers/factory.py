from typing import Optional
from models.exchange import Exchange
from .base_parser import BaseExchangeParser
from .bybit_parser import BybitParser
from .okx_parser import OkxParser
from .mexc_parser import MexcParser
from .bingx_parser import BingXParser
from .coinex_parser import CoinExParser
from .htx_parser import HtxParser
from .kucoin_parser import KucoinParser
from .bitget_parser import BitgetParser
from .poloniex_parser import PoloniexParser

# Маппинг бирж на парсеры
PARSERS = {
    'MEXC': MexcParser,
    'Bybit': BybitParser,
    'BingX': BingXParser,
    'CoinEx': CoinExParser,
    'OKX': OkxParser,
    'HTX': HtxParser,
    'Kucoin': KucoinParser,
    'Poloniex': PoloniexParser,
    'Bitget': BitgetParser,
}


class ExchangeParserFactory:
    """Фабрика для создания парсеров бирж"""
    
    @staticmethod
    def has_parser(exchange_name: str) -> bool:
        """Проверить есть ли парсер для биржи"""
        return exchange_name in PARSERS
    
    @staticmethod
    def create_parser(exchange: Exchange) -> BaseExchangeParser:
        """Создать парсер для биржи"""
        if exchange.name not in PARSERS:
            raise ValueError(f"Parser not found for exchange: {exchange.name}")
        
        if not exchange.spot_api_url or not exchange.kline_api_url:
            raise ValueError(f"Exchange {exchange.name} is missing required API URLs")
        
        parser_class = PARSERS[exchange.name]
        
        # TODO: получить API ключи из БД если нужно
        api_key = None
        api_secret = None
        
        return parser_class(
            exchange.spot_api_url,
            exchange.kline_api_url,
            api_key,
            api_secret
        )
