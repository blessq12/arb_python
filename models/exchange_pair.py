from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal
import aiomysql
from database import Database


class ExchangePair:
    """Модель валютной пары на бирже"""
    
    def __init__(self, id: int, exchange_id: int, base_currency: str, quote_currency: str,
                 symbol_on_exchange: str, is_active: bool = True,
                 last_bid_price: Optional[Decimal] = None,
                 last_ask_price: Optional[Decimal] = None,
                 last_price_update: Optional[datetime] = None,
                 volume_24h: Optional[Decimal] = None,
                 taker_fee: Optional[Decimal] = None,
                 maker_fee: Optional[Decimal] = None,
                 min_amount: Optional[Decimal] = None,
                 **kwargs):
        self.id = id
        self.exchange_id = exchange_id
        self.base_currency = base_currency.upper()
        self.quote_currency = quote_currency.upper()
        self.symbol_on_exchange = symbol_on_exchange
        self.is_active = is_active
        self.last_bid_price = float(last_bid_price) if last_bid_price else None
        self.last_ask_price = float(last_ask_price) if last_ask_price else None
        self.last_price_update = last_price_update
        self.volume_24h = float(volume_24h) if volume_24h else None
        self.taker_fee = float(taker_fee) if taker_fee else None
        self.maker_fee = float(maker_fee) if maker_fee else None
        self.min_amount = float(min_amount) if min_amount else None
        self.exchange = None  # Будет загружен через relation
    
    @property
    def symbol(self) -> str:
        """Получить символ пары"""
        return f"{self.base_currency}{self.quote_currency}"
    
    async def update_prices(self, bid: float, ask: float, volume_24h: Optional[float] = None):
        """Обновить цены пары"""
        query = """
            UPDATE exchange_pairs 
            SET last_bid_price = %s, 
                last_ask_price = %s, 
                volume_24h = %s,
                last_price_update = NOW()
            WHERE id = %s
        """
        await Database.execute_query(query, (bid, ask, volume_24h, self.id), fetch=False)
        self.last_bid_price = bid
        self.last_ask_price = ask
        if volume_24h:
            self.volume_24h = volume_24h
        self.last_price_update = datetime.now()
    
    @staticmethod
    async def get_active_for_arbitrage() -> List['ExchangePair']:
        """Получить все активные пары для арбитража"""
        query = """
            SELECT ep.* 
            FROM exchange_pairs ep
            INNER JOIN exchanges e ON e.id = ep.exchange_id
            WHERE ep.is_active = 1 AND e.is_active = 1
        """
        rows = await Database.execute_query(query)
        pairs = [ExchangePair(**row) for row in rows]
        
        # Загружаем exchange для каждой пары
        exchange_ids = {pair.exchange_id for pair in pairs}
        from models.exchange import Exchange
        exchanges = {ex.id: ex for ex in await Exchange.get_active()}
        for pair in pairs:
            pair.exchange = exchanges.get(pair.exchange_id)
        
        return pairs
    
    @staticmethod
    async def get_by_exchange(exchange_id: int) -> List['ExchangePair']:
        """Получить все активные пары для биржи"""
        query = """
            SELECT * FROM exchange_pairs 
            WHERE exchange_id = %s AND is_active = 1
        """
        rows = await Database.execute_query(query, (exchange_id,))
        return [ExchangePair(**row) for row in rows]
    
    @staticmethod
    async def get_by_symbol(base: str, quote: str) -> List['ExchangePair']:
        """Получить все пары по символу на всех биржах"""
        query = """
            SELECT ep.* 
            FROM exchange_pairs ep
            INNER JOIN exchanges e ON e.id = ep.exchange_id
            WHERE ep.base_currency = %s 
                AND ep.quote_currency = %s 
                AND ep.is_active = 1 
                AND e.is_active = 1
        """
        rows = await Database.execute_query(query, (base.upper(), quote.upper()))
        pairs = [ExchangePair(**row) for row in rows]
        
        # Загружаем exchange
        from models.exchange import Exchange
        exchanges = {ex.id: ex for ex in await Exchange.get_active()}
        for pair in pairs:
            pair.exchange = exchanges.get(pair.exchange_id)
        
        return pairs
    
    @staticmethod
    async def first_or_create(exchange_id: int, base: str, quote: str, 
                              symbol_on_exchange: str, defaults: Optional[Dict] = None) -> 'ExchangePair':
        """Найти или создать пару"""
        query = """
            SELECT * FROM exchange_pairs 
            WHERE exchange_id = %s 
                AND base_currency = %s 
                AND quote_currency = %s
        """
        rows = await Database.execute_query(query, (exchange_id, base.upper(), quote.upper()))
        
        if rows:
            return ExchangePair(**rows[0])
        
        # Создаём новую
        defaults = defaults or {}
        is_active = defaults.get('is_active', True)
        
        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                insert_query = """
                    INSERT INTO exchange_pairs 
                    (exchange_id, base_currency, quote_currency, symbol_on_exchange, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """
                await cursor.execute(
                    insert_query, 
                    (exchange_id, base.upper(), quote.upper(), symbol_on_exchange, is_active)
                )
                await conn.commit()
                
                # Получаем созданную запись
                select_query = """
                    SELECT * FROM exchange_pairs 
                    WHERE exchange_id = %s 
                        AND base_currency = %s 
                        AND quote_currency = %s
                """
                await cursor.execute(select_query, (exchange_id, base.upper(), quote.upper()))
                row = await cursor.fetchone()
                return ExchangePair(**row) if row else None
    
    @staticmethod
    async def get_or_create_for_exchange(exchange_id: int, base: str, quote: str, 
                                        symbol_on_exchange: str) -> 'ExchangePair':
        """Найти или создать пару для биржи (упрощенная версия для нового подхода)"""
        return await ExchangePair.first_or_create(
            exchange_id, 
            base, 
            quote, 
            symbol_on_exchange,
            defaults={'is_active': True}
        )
