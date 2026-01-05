import asyncio
import logging
from datetime import datetime
from database import Database
from parsers.factory import ExchangeParserFactory
from services import ExchangePollingService, ArbitrageAnalysisService, NotificationService
from models.setting import Setting

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArbitrageCoordinator:
    """Координатор процесса арбитража"""
    
    def __init__(self, skip_polling: bool = False):
        self.skip_polling = skip_polling
        self.session_id = f"arb_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.parser_factory = ExchangeParserFactory()
        self.polling_service = ExchangePollingService(self.parser_factory)
        self.arbitrage_service = ArbitrageAnalysisService()
        self.notification_service = NotificationService()
    
    async def run(self):
        """Запустить полный цикл арбитража"""
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"🎯 [{self.session_id}] Запуск координатора арбитража")
        
        try:
            results = {
                'session_id': self.session_id,
                'start_time': datetime.now(),
                'polling_completed': False,
                'analysis_completed': False,
                'opportunities_found': 0,
                'opportunities_saved': 0,
                'alerts_sent': 0,
            }
            
            # Этап 1: Опрос бирж
            if not self.skip_polling:
                logger.info(f"📊 [{self.session_id}] Этап 1: Опрос бирж...")
                polling_results = await self.polling_service.poll_all_exchanges()
                results['polling_completed'] = True
                results['polling_results'] = polling_results
                logger.info(f"✅ [{self.session_id}] Опрос бирж завершен")
            else:
                logger.info(f"⏭️ [{self.session_id}] Опрос бирж пропущен")
                results['polling_completed'] = True
            
            # Этап 2: Анализ арбитража
            logger.info(f"🔍 [{self.session_id}] Этап 2: Анализ арбитражных возможностей...")
            opportunities = await self.arbitrage_service.analyze_arbitrage()
            results['opportunities_found'] = len(opportunities)
            
            if not opportunities:
                logger.info(f"📊 [{self.session_id}] Арбитражных возможностей не найдено")
                await self._log_results(results, start_time)
                return
            
            logger.info(f"📊 [{self.session_id}] Найдено {results['opportunities_found']} арбитражных возможностей")
            
            # Этап 3: Сохранение возможностей
            logger.info(f"💾 [{self.session_id}] Этап 3: Сохранение возможностей в базу...")
            saved = await self.arbitrage_service.save_opportunities(opportunities)
            results['opportunities_saved'] = saved
            results['analysis_completed'] = True
            logger.info(f"✅ [{self.session_id}] Сохранено {saved} возможностей")
            
            # Этап 4: Получение возможностей для алерта
            logger.info(f"🔔 [{self.session_id}] Этап 4: Проверка возможностей для алерта...")
            alert_opportunities = await self.arbitrage_service.get_opportunities_for_alert()
            
            if not alert_opportunities:
                logger.info(f"📢 [{self.session_id}] Нет новых возможностей для алерта")
                await self._log_results(results, start_time)
                return
            
            logger.info(f"📢 [{self.session_id}] Найдено {len(alert_opportunities)} возможностей для алерта")
            
            # Этап 5: Отправка уведомлений
            logger.info(f"📤 [{self.session_id}] Этап 5: Отправка уведомлений...")
            sent_count = await self.notification_service.send_arbitrage_alerts(alert_opportunities)
            results['alerts_sent'] = sent_count
            logger.info(f"✅ [{self.session_id}] Отправлено {sent_count} алертов")
            
            # Логируем финальные результаты
            await self._log_results(results, start_time)
        
        except Exception as e:
            error = f"Ошибка в координаторе арбитража: {e}"
            logger.error(f"❌ [{self.session_id}] {error}", exc_info=True)
            await self.notification_service.send_error_message(error)
    
    async def _log_results(self, results: dict, start_time: float):
        """Логировать результаты координатора"""
        execution_time = asyncio.get_event_loop().time() - start_time
        results['execution_time'] = round(execution_time, 2)
        results['end_time'] = datetime.now()
        
        logger.info(f"🎯 [{self.session_id}] Результаты координатора арбитража:")
        logger.info(f"   ⏱️ Время выполнения: {results['execution_time']}с")
        logger.info(f"   📊 Найдено возможностей: {results['opportunities_found']}")
        logger.info(f"   💾 Сохранено: {results['opportunities_saved']}")
        logger.info(f"   📤 Отправлено алертов: {results['alerts_sent']}")
        
        # Отправляем сводку в Telegram
        summary = (
            f"🎯 *Результаты арбитража*\n\n"
            f"🆔 Сессия: `{self.session_id}`\n"
            f"⏱️ Время выполнения: {results['execution_time']}с\n"
            f"📊 Найдено возможностей: {results['opportunities_found']}\n"
            f"💾 Сохранено: {results['opportunities_saved']}\n"
            f"📤 Отправлено алертов: {results['alerts_sent']}"
        )
        await self.notification_service.send_analysis_result(summary)


async def main():
    """Главная функция"""
    import sys
    
    skip_polling = '--skip-polling' in sys.argv
    
    # Инициализируем БД pool
    await Database.get_pool()
    
    try:
        coordinator = ArbitrageCoordinator(skip_polling=skip_polling)
        await coordinator.run()
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
    finally:
        # Закрываем БД pool
        await Database.close_pool()


if __name__ == "__main__":
    asyncio.run(main())
