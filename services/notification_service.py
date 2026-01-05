import aiohttp
import logging
from typing import List
from config import Config
from models.arbitrage_opportunity import ArbitrageOpportunity

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений в Telegram"""
    
    def __init__(self):
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def is_configured(self) -> bool:
        """Проверить настроен ли Telegram"""
        return bool(self.bot_token and self.chat_id)
    
    async def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """Отправить сообщение в Telegram"""
        if not self.is_configured():
            logger.warning('Telegram не настроен: отсутствует токен или ID чата')
            return False
        
        url = f"{self.base_url}/sendMessage"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={
                    'chat_id': self.chat_id,
                    'text': message,
                    'parse_mode': parse_mode,
                    'disable_web_page_preview': True,
                }, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        logger.info('Сообщение отправлено в Telegram')
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f'Ошибка отправки в Telegram: {response.status} - {error_text}')
                        return False
        except Exception as e:
            logger.error(f'Исключение при отправке в Telegram: {e}')
            return False
    
    async def send_arbitrage_alerts(self, opportunities: List[ArbitrageOpportunity]) -> int:
        """Отправить алерты для всех возможностей одним сообщением"""
        if not self.is_configured():
            logger.warning('Telegram не настроен, алерты не отправлены')
            return 0
        
        if not opportunities:
            logger.info('Нет арбитражных возможностей для отправки')
            return 0
        
        try:
            message = await self._format_arbitrage_summary(opportunities)
            success = await self.send_message(message)
            
            if success:
                # Помечаем все возможности как отправленные
                for opp in opportunities:
                    await opp.mark_alerted()
                
                logger.info(f'Сводка арбитражных возможностей отправлена ({len(opportunities)} возможностей)')
                return len(opportunities)
            else:
                logger.error('Не удалось отправить сводку арбитражных возможностей')
                return 0
        except Exception as e:
            logger.error(f'Ошибка при отправке сводки: {e}')
            return 0
    
    async def _format_arbitrage_summary(self, opportunities: List[ArbitrageOpportunity]) -> str:
        """Форматирует сводку арбитражных возможностей"""
        if not opportunities:
            return "Нет арбитражных возможностей"
        
        # Загружаем все биржи сразу
        from models.exchange import Exchange
        all_exchanges = await Exchange.get_active()
        exchanges_dict = {ex.id: ex.name for ex in all_exchanges}
        
        message = f"💰 <b>Арбитражные возможности ({len(opportunities)})</b>\n\n"
        
        for opp in opportunities[:10]:  # Ограничиваем до 10 для читаемости
            buy_name = exchanges_dict.get(opp.buy_exchange_id, f"Биржа {opp.buy_exchange_id}")
            sell_name = exchanges_dict.get(opp.sell_exchange_id, f"Биржа {opp.sell_exchange_id}")
            
            message += (
                f"📈 <b>{opp.base_currency}/{opp.quote_currency}</b>\n"
                f"   Купить: <b>{buy_name}</b> @ {opp.buy_price:.8f}\n"
                f"   Продать: <b>{sell_name}</b> @ {opp.sell_price:.8f}\n"
                f"   Профит: <b>{opp.profit_percent:.4f}%</b> (после комиссий: {opp.net_profit_percent:.4f}%)\n"
                f"   Доход: ${opp.profit_usd:.2f} на $1000\n\n"
            )
        
        if len(opportunities) > 10:
            message += f"\n... и еще {len(opportunities) - 10} возможностей"
        
        total_profit = sum(opp.profit_usd for opp in opportunities)
        avg_profit = total_profit / len(opportunities) if opportunities else 0
        
        message += f"\n━━━━━━━━━━━━━━━━━━━━\n"
        message += f"📊 <b>Итого:</b>\n"
        message += f"   • Всего: {len(opportunities)}\n"
        message += f"   • Средний профит: ${avg_profit:.2f}\n"
        message += f"   • Общий профит: ${total_profit:.2f}"
        
        return message
    
    async def send_error_message(self, error: str) -> bool:
        """Отправить сообщение об ошибке"""
        message = f"❌ <b>Ошибка системы</b>\n\n{error}"
        return await self.send_message(message)
    
    async def send_analysis_result(self, message: str) -> bool:
        """Отправить результат анализа"""
        return await self.send_message(message)
