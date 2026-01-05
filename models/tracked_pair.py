from typing import List, Optional
from database import Database


class TrackedPair:
    """Модель отслеживаемых валютных пар (без привязки к биржам)
    
    Пары берутся из таблицы exchange_pairs - все уникальные активные комбинации
    base_currency + quote_currency. Управление через Laravel админку.
    """
    
    def __init__(self, base_currency: str, quote_currency: str, is_active: bool = True, **kwargs):
        self.base_currency = base_currency.upper()
        self.quote_currency = quote_currency.upper()
        self.is_active = is_active
    
    @property
    def symbol(self) -> str:
        """Получить символ пары"""
        return f"{self.base_currency}{self.quote_currency}"
    
    @staticmethod
    async def get_all_active() -> List['TrackedPair']:
        """Получить все активные отслеживаемые пары из exchange_pairs
        
        Берет все уникальные комбинации base_currency + quote_currency
        где is_active = 1. Управление через Laravel админку.
        """
        query = """
            SELECT DISTINCT base_currency, quote_currency
            FROM exchange_pairs
            WHERE is_active = 1
            ORDER BY base_currency, quote_currency
        """
        rows = await Database.execute_query(query)
        return [
            TrackedPair(
                base_currency=row['base_currency'],
                quote_currency=row['quote_currency'],
                is_active=True
            )
            for row in rows
        ]
    
    @staticmethod
    async def create_if_not_exists(base: str, quote: str) -> 'TrackedPair':
        """Создать объект пары (пары управляются через exchange_pairs в БД)"""
        return TrackedPair(base_currency=base, quote_currency=quote)
