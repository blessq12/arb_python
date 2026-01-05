import aiomysql
import asyncio
from config import Config
from typing import Optional, List, Dict, Any


class Database:
    _pool: Optional[aiomysql.Pool] = None
    
    @classmethod
    async def get_pool(cls) -> aiomysql.Pool:
        """Singleton для async connection pool"""
        if cls._pool is None:
            cls._pool = await aiomysql.create_pool(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USERNAME,
                password=Config.DB_PASSWORD,
                db=Config.DB_DATABASE,
                minsize=2,
                maxsize=10,
                autocommit=False
            )
        return cls._pool
    
    @classmethod
    async def execute_query(cls, query: str, params: Optional[tuple] = None, fetch: bool = True) -> Any:
        """Выполнить async запрос и вернуть результат"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                try:
                    await cursor.execute(query, params or ())
                    if fetch and query.strip().upper().startswith('SELECT'):
                        result = await cursor.fetchall()
                    else:
                        await conn.commit()
                        result = cursor.rowcount if not fetch else await cursor.fetchall()
                    return result
                except Exception as e:
                    await conn.rollback()
                    raise e
    
    @classmethod
    async def close_pool(cls):
        """Закрыть pool соединений"""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
