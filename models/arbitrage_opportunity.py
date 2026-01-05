from typing import Optional, List, Dict
from datetime import datetime
from decimal import Decimal
import aiomysql
from database import Database


class ArbitrageOpportunity:
    """Модель арбитражной возможности"""
    
    def __init__(self, buy_exchange_id: int, sell_exchange_id: int,
                 base_currency: str, quote_currency: str, buy_price: float, sell_price: float,
                 profit_percent: float, profit_usd: float, net_profit_percent: float,
                 volume_24h_buy: float, volume_24h_sell: float, min_volume_usd: float,
                 buy_commission: float, sell_commission: float, total_commission: float,
                 id: Optional[int] = None,
                 is_active: bool = True, detected_at: Optional[datetime] = None,
                 alerted_at: Optional[datetime] = None, expired_at: Optional[datetime] = None,
                 **kwargs):
        self.id = id
        self.buy_exchange_id = buy_exchange_id
        self.sell_exchange_id = sell_exchange_id
        self.base_currency = base_currency.upper()
        self.quote_currency = quote_currency.upper()
        self.buy_price = float(buy_price)
        self.sell_price = float(sell_price)
        self.profit_percent = float(profit_percent)
        self.profit_usd = float(profit_usd)
        self.net_profit_percent = float(net_profit_percent)
        self.volume_24h_buy = float(volume_24h_buy)
        self.volume_24h_sell = float(volume_24h_sell)
        self.min_volume_usd = float(min_volume_usd)
        self.buy_commission = float(buy_commission)
        self.sell_commission = float(sell_commission)
        self.total_commission = float(total_commission)
        self.is_active = is_active
        self.detected_at = detected_at or datetime.now()
        self.alerted_at = alerted_at
        self.expired_at = expired_at
    
    async def save(self) -> int:
        """Сохранить или обновить возможность"""
        # Проверяем существует ли уже
        query = """
            SELECT id FROM arbitrage_opportunities 
            WHERE buy_exchange_id = %s 
                AND sell_exchange_id = %s 
                AND base_currency = %s 
                AND quote_currency = %s 
                AND is_active = 1
        """
        existing = await Database.execute_query(
            query, 
            (self.buy_exchange_id, self.sell_exchange_id, self.base_currency, self.quote_currency)
        )
        
        if existing:
            # Обновляем
            query = """
                UPDATE arbitrage_opportunities 
                SET buy_price = %s, sell_price = %s, profit_percent = %s, profit_usd = %s,
                    net_profit_percent = %s, volume_24h_buy = %s, volume_24h_sell = %s,
                    min_volume_usd = %s, buy_commission = %s, sell_commission = %s,
                    total_commission = %s, detected_at = %s
                WHERE id = %s
            """
            await Database.execute_query(
                query,
                (self.buy_price, self.sell_price, self.profit_percent, self.profit_usd,
                 self.net_profit_percent, self.volume_24h_buy, self.volume_24h_sell,
                 self.min_volume_usd, self.buy_commission, self.sell_commission,
                 self.total_commission, self.detected_at, existing[0]['id']),
                fetch=False
            )
            return existing[0]['id']
        else:
            # Создаём новую
            query = """
                INSERT INTO arbitrage_opportunities 
                (buy_exchange_id, sell_exchange_id, base_currency, quote_currency,
                 buy_price, sell_price, profit_percent, profit_usd, net_profit_percent,
                 volume_24h_buy, volume_24h_sell, min_volume_usd,
                 buy_commission, sell_commission, total_commission,
                 is_active, detected_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            pool = await Database.get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        query,
                        (self.buy_exchange_id, self.sell_exchange_id, self.base_currency, 
                         self.quote_currency, self.buy_price, self.sell_price, self.profit_percent,
                         self.profit_usd, self.net_profit_percent, self.volume_24h_buy,
                         self.volume_24h_sell, self.min_volume_usd, self.buy_commission,
                         self.sell_commission, self.total_commission, self.is_active, self.detected_at)
                    )
                    await conn.commit()
                    return cursor.lastrowid
    
    @staticmethod
    async def get_for_alert(min_profit: float = 0.0, min_volume: float = 100.0) -> List['ArbitrageOpportunity']:
        """Получить возможности для алерта из БД (активные, прибыльные, недавние)
        
        Проверяет net_profit_percent (после комиссий) и учитывает кулдаун между алертами
        """
        from models.setting import Setting
        
        # Получаем кулдаун из настроек БД
        alert_cooldown_minutes = await Setting.get('alert_cooldown_minutes', 30)
        
        query = """
            SELECT * FROM arbitrage_opportunities 
            WHERE is_active = 1 
                AND net_profit_percent >= %s
                AND volume_24h_buy >= %s 
                AND volume_24h_sell >= %s
                AND detected_at >= DATE_SUB(NOW(), INTERVAL 30 MINUTE)
                AND (alerted_at IS NULL OR alerted_at < DATE_SUB(NOW(), INTERVAL %s MINUTE))
            ORDER BY net_profit_percent DESC
            LIMIT 20
        """
        rows = await Database.execute_query(query, (min_profit, min_volume, min_volume, alert_cooldown_minutes))
        return [ArbitrageOpportunity(**row) for row in rows]
    
    async def mark_alerted(self):
        """Отметить что алерт отправлен"""
        query = "UPDATE arbitrage_opportunities SET alerted_at = NOW() WHERE id = %s"
        await Database.execute_query(query, (self.id,), fetch=False)
        self.alerted_at = datetime.now()
