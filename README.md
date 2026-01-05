# Python Arbitrage System

Асинхронная система поиска арбитражных возможностей между биржами на Python.

## Архитектура

### Преимущества async/await над PHP:
- ✅ Настоящая асинхронность (не через очереди)
- ✅ Параллельный опрос бирж без блокировок
- ✅ Эффективное использование ресурсов
- ✅ Простота координации через `asyncio.gather()`

### Структура проекта:

```
python/
├── main.py                    # Точка входа, координатор
├── database.py                # Async БД (aiomysql)
├── config.py                  # Конфигурация
│
├── models/                    # Модели данных
│   ├── exchange.py           # Биржи
│   ├── exchange_pair.py      # Валютные пары
│   ├── arbitrage_opportunity.py
│   └── setting.py
│
├── parsers/                   # Парсеры бирж (async)
│   ├── base_parser.py
│   ├── bybit_parser.py
│   ├── okx_parser.py
│   └── factory.py
│
└── services/                  # Бизнес-логика
    ├── exchange_polling_service.py  # Опрос бирж
    ├── arbitrage_service.py         # Анализ арбитража
    └── notification_service.py      # Telegram уведомления
```

## Установка

```bash
# Установить зависимости
pip install -r requirements.txt

# Настроить .env
cp .env.example .env
# Заполнить DB_* и TELEGRAM_* настройки
```

## Использование

```bash
# Полный цикл (опрос + анализ + алерты)
python main.py

# Только анализ (без опроса бирж)
python main.py --skip-polling
```

## Алгоритм работы

1. **Опрос бирж** (`ExchangePollingService`):
   - Параллельный опрос всех активных бирж через `asyncio.gather()`
   - Batch API где возможно (Bybit)
   - Обновление цен в БД

2. **Анализ арбитража** (`ArbitrageAnalysisService`):
   - Группировка пар по символам
   - Построение матрицы цен
   - Расчет профита с учетом комиссий
   - Фильтрация по min_profit и min_volume

3. **Уведомления** (`NotificationService`):
   - Отправка сводки в Telegram
   - Marking opportunities as alerted

## Отличия от PHP версии

| PHP | Python |
|-----|--------|
| Jobs через очереди | `asyncio.gather()` |
| PollExchangeJob (последовательно) | Параллельный опрос всех бирж |
| ArbitrageCoordinatorJob (ожидание) | Единый async координатор |
| Синхронные HTTP запросы | `aiohttp` async запросы |

## TODO

- [ ] Добавить остальные парсеры (MEXC, BingX, CoinEx, HTX, Kucoin, Poloniex, Bitget)
- [ ] Команда для синхронизации символов (`exchanges:sync-symbols`)
- [ ] Команда для получения валют (`exchange:fetch-currencies`)
- [ ] Обработка ошибок и retry логика
- [ ] Метрики и мониторинг
