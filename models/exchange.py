from typing import Optional, List, Dict
from database import Database


class Exchange:
    """Модель биржи"""
    
    def __init__(self, id: int, name: str, spot_api_url: str, kline_api_url: str, 
                 is_active: bool = True, **kwargs):
        self.id = id
        self.name = name
        self.spot_api_url = spot_api_url
        self.kline_api_url = kline_api_url
        self.is_active = is_active
    
    @staticmethod
    async def get_active() -> List['Exchange']:
        """Получить все активные биржи"""
        query = """
            SELECT id, name, spot_api_url, kline_api_url, is_active 
            FROM exchanges 
            WHERE is_active = 1
        """
        rows = await Database.execute_query(query)
        return [Exchange(**row) for row in rows]
    
    @staticmethod
    async def get_by_id(exchange_id: int) -> Optional['Exchange']:
        """Получить биржу по ID"""
        query = """
            SELECT id, name, spot_api_url, kline_api_url, is_active 
            FROM exchanges 
            WHERE id = %s
        """
        rows = await Database.execute_query(query, (exchange_id,))
        if rows:
            return Exchange(**rows[0])
        return None