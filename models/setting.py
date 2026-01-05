from typing import Optional, Any
from database import Database


class Setting:
    """Модель настроек"""
    
    _cache: Optional[dict] = None
    
    @staticmethod
    async def get(key: str, default: Any = None) -> Any:
        """Получить значение настройки"""
        settings = await Setting._get_all()
        return settings.get(key, default)
    
    @staticmethod
    async def _get_all() -> dict:
        """Получить все настройки (с кэшем)"""
        if Setting._cache is None:
            query = "SELECT * FROM settings LIMIT 1"
            rows = await Database.execute_query(query)
            if rows:
                Setting._cache = dict(rows[0])
            else:
                # Создаём дефолтные настройки
                Setting._cache = Setting._get_defaults()
                await Setting._create_defaults()
        return Setting._cache
    
    @staticmethod
    def _get_defaults() -> dict:
        """Дефолтные настройки"""
        return {
            'min_profit_percent': 2.0,
            'min_volume_usd': 100.0,
            'data_lifetime_minutes': 5,
            'alert_cooldown_minutes': 30,
            'mexc_commission': 0.001,
            'bybit_commission': 0.001,
            'bingx_commission': 0.001,
            'coinex_commission': 0.001,
            'okx_commission': 0.0008,
            'htx_commission': 0.002,
            'kucoin_commission': 0.001,
            'poloniex_commission': 0.0015,
            'bitget_commission': 0.001,
        }
    
    @staticmethod
    async def _create_defaults():
        """Создать дефолтные настройки в БД"""
        defaults = Setting._get_defaults()
        query = """
            INSERT INTO settings ({}) 
            VALUES ({})
            ON DUPLICATE KEY UPDATE id=id
        """.format(
            ','.join(defaults.keys()),
            ','.join(['%s'] * len(defaults))
        )
        await Database.execute_query(query, tuple(defaults.values()), fetch=False)
    
    @staticmethod
    def _get_default_commission(exchange_name: str) -> float:
        """Получить дефолтную комиссию для биржи"""
        defaults = Setting._get_defaults()
        commission_key = f"{exchange_name.lower()}_commission"
        return defaults.get(commission_key, 0.001)  # 0.1% по умолчанию
    
    @staticmethod
    async def get_default_commission(exchange_name: str) -> float:
        """Получить комиссию биржи (async версия)"""
        settings = await Setting._get_all()
        commission_key = f"{exchange_name.lower()}_commission"
        return settings.get(commission_key, Setting._get_default_commission(exchange_name))
    
    @staticmethod
    async def flush_cache():
        """Очистить кэш настроек"""
        Setting._cache = None
