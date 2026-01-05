import logging
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from models.exchange_pair import ExchangePair
from models.arbitrage_opportunity import ArbitrageOpportunity
from models.setting import Setting

logger = logging.getLogger(__name__)


class ArbitrageAnalysisService:
    """Сервис для анализа арбитражных возможностей"""
    
    async def analyze_arbitrage(self) -> List[Dict]:
        """Анализирует цены и находит арбитражные возможности"""
        logger.info('🔍 Начинаем анализ арбитража...')
        
        # Получаем все активные пары
        exchange_pairs = await ExchangePair.get_active_for_arbitrage()
        
        if not exchange_pairs:
            logger.info('❌ Нет активных пар для анализа арбитража')
            return []
        
        logger.info(f"📊 Найдено {len(exchange_pairs)} активных пар для анализа")
        
        # Группируем пары по символу (base_currency + quote_currency)
        pairs_by_symbol = defaultdict(list)
        for pair in exchange_pairs:
            symbol_key = f"{pair.base_currency}{pair.quote_currency}"
            pairs_by_symbol[symbol_key].append(pair)
        
        # Получаем пороги из настроек БД
        min_profit = await Setting.get('min_profit_percent', 2.0)
        min_volume = await Setting.get('min_volume_usd', 100.0)
        
        opportunities = []
        total_analyzed = 0
        
        for symbol, pairs_for_symbol in pairs_by_symbol.items():
            # Проверяем что пара торгуется минимум на 2 биржах
            if len(pairs_for_symbol) < 2:
                continue
            
            logger.info(f"🔍 Анализируем пару {symbol} на {len(pairs_for_symbol)} биржах")
            
            symbol_opportunities = await self._analyze_symbol(pairs_for_symbol, min_profit, min_volume)
            opportunities.extend(symbol_opportunities)
            total_analyzed += 1
        
        logger.info(f"📊 Проанализировано {total_analyzed} пар, найдено {len(opportunities)} возможностей")
        
        return opportunities
    
    async def _analyze_symbol(self, pairs_for_symbol: List[ExchangePair], 
                              min_profit: float, min_volume: float) -> List[Dict]:
        """Анализирует конкретную пару на арбитражные возможности"""
        opportunities = []
        
        if not pairs_for_symbol:
            return opportunities
        
        base_currency = pairs_for_symbol[0].base_currency
        quote_currency = pairs_for_symbol[0].quote_currency
        
        # Группируем пары по биржам
        pairs_by_exchange = defaultdict(list)
        for pair in pairs_for_symbol:
            pairs_by_exchange[pair.exchange_id].append(pair)
        
        # Получаем цены из сохраненных данных
        data_lifetime_minutes = await Setting.get('data_lifetime_minutes', 5)
        cutoff_time = datetime.now() - timedelta(minutes=data_lifetime_minutes)
        
        price_matrix = {}
        for exchange_id, pairs_for_exchange in pairs_by_exchange.items():
            exchange_pair = pairs_for_exchange[0]
            exchange = exchange_pair.exchange
            
            # Проверяем свежесть данных
            if not exchange_pair.last_price_update or exchange_pair.last_price_update < cutoff_time:
                logger.info(f"⚠️ Нет свежих цен для {exchange.name}, пропускаем")
                continue
            
            if not exchange_pair.last_bid_price or not exchange_pair.last_ask_price:
                logger.info(f"⚠️ Неполные данные цен для {exchange.name}, пропускаем")
                continue
            
            price_matrix[exchange_id] = {
                'bid': exchange_pair.last_bid_price,
                'ask': exchange_pair.last_ask_price,
                'exchange': exchange,
                'exchange_pair': exchange_pair,
                'volume_24h': exchange_pair.volume_24h or min_volume,
            }
            
            logger.info(f"✅ Используем сохраненную цену для {exchange.name}: "
                       f"Bid={exchange_pair.last_bid_price}, Ask={exchange_pair.last_ask_price}, "
                       f"Volume={price_matrix[exchange_id]['volume_24h']}")
        
        if len(price_matrix) < 2:
            logger.info(f"❌ Недостаточно цен для арбитража по паре {base_currency}{quote_currency}")
            return opportunities
        
        # Сравниваем все комбинации бирж
        exchange_ids = list(price_matrix.keys())
        for i in range(len(exchange_ids)):
            for j in range(i + 1, len(exchange_ids)):
                buy_exchange_id = exchange_ids[i]
                sell_exchange_id = exchange_ids[j]
                
                # Проверяем возможность покупки на первой, продажи на второй
                opportunity1 = await self._calculate_opportunity(
                    base_currency,
                    quote_currency,
                    price_matrix[buy_exchange_id],
                    price_matrix[sell_exchange_id],
                    buy_exchange_id,
                    sell_exchange_id,
                    min_profit,
                    min_volume
                )
                
                if opportunity1:
                    opportunities.append(opportunity1)
                
                # Проверяем обратную возможность
                opportunity2 = await self._calculate_opportunity(
                    base_currency,
                    quote_currency,
                    price_matrix[sell_exchange_id],
                    price_matrix[buy_exchange_id],
                    sell_exchange_id,
                    buy_exchange_id,
                    min_profit,
                    min_volume
                )
                
                if opportunity2:
                    opportunities.append(opportunity2)
        
        return opportunities
    
    async def _calculate_opportunity(self, base_currency: str, quote_currency: str,
                              buy_price: Dict, sell_price: Dict,
                              buy_exchange_id: int, sell_exchange_id: int,
                              min_profit: float, min_volume: float) -> Optional[Dict]:
        """Рассчитывает арбитражную возможность между двумя биржами"""
        buy_price_value = buy_price['ask']  # Покупаем по ask
        sell_price_value = sell_price['bid']  # Продаём по bid
        
        # Рассчитываем базовый профит
        profit_percent = ((sell_price_value - buy_price_value) / buy_price_value) * 100
        
        logger.info(f"💰 {base_currency}{quote_currency}: "
                   f"{buy_price['exchange'].name} -> {sell_price['exchange'].name}, "
                   f"профит: {profit_percent:.4f}%")
        
        if profit_percent <= 0:
            logger.info(f"❌ Нет профита для {base_currency}{quote_currency}")
            return None
        
        # Получаем комиссии
        buy_commission = float(buy_price['exchange_pair'].taker_fee or await Setting.get_default_commission(buy_price['exchange'].name))
        sell_commission = float(sell_price['exchange_pair'].taker_fee or await Setting.get_default_commission(sell_price['exchange'].name))
        total_commission = buy_commission + sell_commission
        
        # Рассчитываем чистый профит после комиссий
        net_profit_percent = profit_percent - (total_commission * 100)
        
        logger.info(f"💱 Комиссии: {buy_price['exchange'].name}={buy_commission*100:.4f}% + "
                   f"{sell_price['exchange'].name}={sell_commission*100:.4f}% = {total_commission*100:.4f}%")
        logger.info(f"📊 Чистый профит: {net_profit_percent:.4f}% (минимум {min_profit}%)")
        
        # Проверяем что чистый профит (после комиссий) соответствует минимальному порогу
        if net_profit_percent < min_profit:
            logger.info(f"❌ Профит {net_profit_percent:.4f}% ниже минимума {min_profit}% для {base_currency}{quote_currency}")
            return None
        
        # Рассчитываем профит в USD (при объёме $1000)
        profit_usd = (net_profit_percent / 100) * 1000
        
        # Используем реальные объемы или минимальный
        volume_24h_buy = max(buy_price['volume_24h'] or min_volume, min_volume)
        volume_24h_sell = max(sell_price['volume_24h'] or min_volume, min_volume)
        
        logger.info(f"📈 Объемы: {buy_price['exchange'].name}={volume_24h_buy}$ "
                   f"{sell_price['exchange'].name}={volume_24h_sell}$ (минимум {min_volume}$)")
        
        return {
            'buy_exchange_id': buy_exchange_id,
            'sell_exchange_id': sell_exchange_id,
            'base_currency': base_currency,
            'quote_currency': quote_currency,
            'buy_price': buy_price_value,
            'sell_price': sell_price_value,
            'profit_percent': profit_percent,
            'profit_usd': profit_usd,
            'volume_24h_buy': volume_24h_buy,
            'volume_24h_sell': volume_24h_sell,
            'min_volume_usd': min_volume,
            'buy_commission': buy_commission,
            'sell_commission': sell_commission,
            'total_commission': total_commission,
            'net_profit_percent': net_profit_percent,
            'is_active': True,
            'detected_at': datetime.now(),
        }
    
    async def save_opportunities(self, opportunities: List[Dict]) -> int:
        """Сохраняет найденные возможности в базу данных"""
        if not opportunities:
            return 0
        
        logger.info(f"💾 Пытаемся сохранить {len(opportunities)} возможностей")
        
        saved = 0
        for opp_data in opportunities:
            try:
                opportunity = ArbitrageOpportunity(**opp_data)
                await opportunity.save()
                saved += 1
                logger.info(f"💾 Сохранено: {opp_data['buy_exchange_id']} -> "
                          f"{opp_data['sell_exchange_id']} для пары "
                          f"{opp_data['base_currency']}{opp_data['quote_currency']}")
            except Exception as e:
                logger.error(f"❌ Ошибка при сохранении: {e}")
        
        return saved
    
    async def get_opportunities_for_alert(self) -> List[ArbitrageOpportunity]:
        """Получает возможности готовые для алерта из настроек БД"""
        min_profit = await Setting.get('min_profit_percent', 2.0)
        min_volume = await Setting.get('min_volume_usd', 100.0)
        return await ArbitrageOpportunity.get_for_alert(min_profit, min_volume)
