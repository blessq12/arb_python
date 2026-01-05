import asyncio
import logging
from typing import List, Dict, Set, Optional
from models.exchange import Exchange
from models.exchange_pair import ExchangePair
from models.tracked_pair import TrackedPair
from parsers.factory import ExchangeParserFactory

logger = logging.getLogger(__name__)


class ExchangePollingService:
    """Сервис для опроса бирж и обновления цен"""
    
    def __init__(self, parser_factory: ExchangeParserFactory):
        self.parser_factory = parser_factory
        self._exchange_symbols_cache: Dict[int, Set[str]] = {}  # Кэш символов бирж
    
    async def poll_all_exchanges(self) -> Dict[str, Dict[str, int]]:
        """Опросить все активные биржи параллельно"""
        exchanges = await Exchange.get_active()
        tracked_pairs = await TrackedPair.get_all_active()
        
        if not exchanges:
            logger.warning("Нет активных бирж для опроса")
            return {}
        
        if not tracked_pairs:
            logger.warning("Нет отслеживаемых пар")
            return {}
        
        logger.info(f"🔄 Начинаем опрос {len(exchanges)} бирж по {len(tracked_pairs)} отслеживаемым парам...")
        
        # Параллельный опрос всех бирж
        tasks = [self.poll_exchange(exchange, tracked_pairs) for exchange in exchanges]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        summary = {}
        for exchange, result in zip(exchanges, results):
            if isinstance(result, Exception):
                logger.error(f"❌ Ошибка при опросе {exchange.name}: {result}")
                summary[exchange.name] = {'successful': 0, 'errors': 0, 'total': 0, 'not_found': 0}
            else:
                summary[exchange.name] = result
        
        return summary
    
    async def poll_exchange(self, exchange: Exchange, tracked_pairs: List[TrackedPair]) -> Dict[str, int]:
        """Опросить одну биржу для всех отслеживаемых пар"""
        if not self.parser_factory.has_parser(exchange.name):
            logger.warning(f"⚠️ Парсер для биржи {exchange.name} не найден")
            return {'successful': 0, 'errors': 0, 'total': 0, 'not_found': 0}
        
        logger.info(f"🔄 Опрашиваем {exchange.name} ({len(tracked_pairs)} пар для проверки)...")
        
        try:
            parser = self.parser_factory.create_parser(exchange)
            
            # Получаем кэшированный список символов биржи (если доступен)
            exchange_symbols = await self._get_exchange_symbols(exchange, parser)
            
            successful = 0
            errors = 0
            not_found = 0
            
            # Фильтруем только те пары, которые есть на бирже
            pairs_to_poll = []
            for tracked_pair in tracked_pairs:
                # Ищем символ на бирже
                found_symbol = None
                
                if exchange_symbols:
                    # Если есть кэш символов - используем его
                    symbol_variants = [
                        tracked_pair.symbol,  # BTCUSDT
                        f"{tracked_pair.base_currency}/{tracked_pair.quote_currency}",  # BTC/USDT
                        f"{tracked_pair.base_currency}-{tracked_pair.quote_currency}",  # BTC-USDT
                        f"{tracked_pair.base_currency}_{tracked_pair.quote_currency}",  # BTC_USDT
                    ]
                    
                    for variant in symbol_variants:
                        normalized = parser.normalize_symbol(variant)
                        if normalized in exchange_symbols:
                            found_symbol = normalized
                            break
                else:
                    # Если нет кэша - пробуем стандартный формат (будет проверка при запросе)
                    # Используем самый вероятный формат для биржи
                    base_format = {
                        'BingX': f"{tracked_pair.base_currency}-{tracked_pair.quote_currency}",
                        'MEXC': tracked_pair.symbol,
                        'CoinEx': tracked_pair.symbol,
                        'HTX': tracked_pair.symbol.lower(),
                        'Kucoin': f"{tracked_pair.base_currency}-{tracked_pair.quote_currency}",
                    }
                    found_symbol = parser.normalize_symbol(
                        base_format.get(exchange.name, tracked_pair.symbol)
                    )
                
                if found_symbol:
                    pairs_to_poll.append((tracked_pair, found_symbol))
                else:
                    not_found += 1
            
            logger.info(f"📊 {exchange.name}: найдено {len(pairs_to_poll)} пар из {len(tracked_pairs)} (пропущено {not_found})")
            
            if not pairs_to_poll:
                await parser.close()
                return {'successful': 0, 'errors': 0, 'total': len(tracked_pairs), 'not_found': not_found}
            
            # Параллельный опрос всех найденных пар
            tasks = [self._poll_tracked_pair(exchange, parser, tracked_pair, symbol) 
                    for tracked_pair, symbol in pairs_to_poll]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                elif result:
                    successful += 1
                else:
                    errors += 1
            
            logger.info(f"✅ Биржа {exchange.name}: {successful}/{len(pairs_to_poll)} успешно, {errors} ошибок, {not_found} не найдено")
            
            await parser.close()
            
            return {'successful': successful, 'errors': errors, 'total': len(tracked_pairs), 'not_found': not_found}
        
        except Exception as e:
            logger.error(f"❌ Ошибка при опросе {exchange.name}: {e}")
            return {'successful': 0, 'errors': len(tracked_pairs), 'total': len(tracked_pairs), 'not_found': 0}
    
    async def _get_exchange_symbols(self, exchange: Exchange, parser) -> Set[str]:
        """Получить и закэшировать список символов биржи"""
        if exchange.id not in self._exchange_symbols_cache:
            try:
                symbols = await parser.get_all_symbols()
                if symbols:
                    # Нормализуем все символы для быстрого поиска
                    normalized_symbols = {parser.normalize_symbol(s) for s in symbols}
                    self._exchange_symbols_cache[exchange.id] = normalized_symbols
                    logger.debug(f"📋 {exchange.name}: закэшировано {len(normalized_symbols)} символов")
                else:
                    # Пустой список - значит биржа не поддерживает getAllSymbols
                    # Будем пробовать запрашивать напрямую
                    self._exchange_symbols_cache[exchange.id] = set()
                    logger.debug(f"📋 {exchange.name}: getAllSymbols не поддерживается, будем пробовать запрашивать напрямую")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить список символов для {exchange.name}: {e}")
                self._exchange_symbols_cache[exchange.id] = set()
        
        return self._exchange_symbols_cache[exchange.id]
    
    async def _poll_tracked_pair(self, exchange: Exchange, parser, tracked_pair: TrackedPair, symbol: str) -> bool:
        """Опросить одну отслеживаемую пару на бирже"""
        try:
            ticker = await parser.get_ticker(symbol)
            
            # Находим или создаем запись в exchange_pairs
            exchange_pair = await ExchangePair.get_or_create_for_exchange(
                exchange.id,
                tracked_pair.base_currency,
                tracked_pair.quote_currency,
                symbol
            )
            
            # Обновляем цены
            await exchange_pair.update_prices(
                ticker['bid'],
                ticker['ask'],
                ticker.get('volume_24h')
            )
            
            return True
        except Exception as e:
            # Игнорируем ошибки "пара не найдена" - это нормально
            error_msg = str(e).lower()
            if any(x in error_msg for x in ['not found', 'invalid symbol', '400', 'bad request', 'symbol']):
                # Пара не существует на бирже - это нормально, просто пропускаем
                return False
            else:
                logger.warning(f"Ошибка при получении цены {symbol} с {exchange.name}: {e}")
            return False
