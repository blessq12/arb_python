import asyncio
from database import Database
from models.exchange_pair import ExchangePair

async def check():
    await Database.get_pool()
    pairs = await ExchangePair.get_active_for_arbitrage()
    print(f'📊 Всего активных пар: {len(pairs)}\n')
    
    # Группируем по символам
    by_symbol = {}
    for p in pairs:
        symbol = f"{p.base_currency}/{p.quote_currency}"
        if symbol not in by_symbol:
            by_symbol[symbol] = []
        exchange_name = p.exchange.name if p.exchange else f"Биржа {p.exchange_id}"
        by_symbol[symbol].append(exchange_name)
    
    print(f'📈 Уникальных символов: {len(by_symbol)}\n')
    print('Пары для анализа (те что торгуются на 2+ биржах):')
    print('-' * 60)
    
    for symbol, exchanges in sorted(by_symbol.items()):
        if len(exchanges) >= 2:
            print(f"{symbol}: {len(exchanges)} бирж - {', '.join(exchanges)}")
    
    await Database.close_pool()

if __name__ == "__main__":
    asyncio.run(check())
