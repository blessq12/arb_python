import asyncio
from database import Database

async def check():
    await Database.get_pool()
    rows = await Database.execute_query(
        'SELECT id, base_currency, quote_currency, buy_exchange_id, sell_exchange_id, '
        'profit_percent, net_profit_percent, buy_price, sell_price '
        'FROM arbitrage_opportunities WHERE is_active=1 ORDER BY id DESC LIMIT 10'
    )
    print(f'📊 Найдено {len(rows)} активных возможностей:\n')
    for r in rows:
        print(f"  {r['base_currency']}/{r['quote_currency']}: "
              f"биржа {r['buy_exchange_id']} -> {r['sell_exchange_id']}, "
              f"профит {r['profit_percent']:.4f}%, "
              f"чистый {r['net_profit_percent']:.4f}%, "
              f"цены {r['buy_price']:.2f} -> {r['sell_price']:.2f}")
    await Database.close_pool()

if __name__ == "__main__":
    asyncio.run(check())
