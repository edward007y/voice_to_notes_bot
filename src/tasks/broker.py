from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from taskiq import SimpleRetryMiddleware, TaskiqEvents, TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from src.core.config import settings

result_backend = RedisAsyncResultBackend(
    redis_url=settings.redis_url,
)

broker = ListQueueBroker(url=settings.redis_url).with_middlewares(
    SimpleRetryMiddleware(default_retry_count=3)
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_broker(state: TaskiqState) -> None:
    """Виконується при запуску worker-процесу. Ініціалізуємо Bot."""
    state.bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_broker(state: TaskiqState) -> None:
    """Виконується при зупинці worker-процесу. Закриваємо сесію."""
    if hasattr(state, "bot"):
        await state.bot.session.close()
