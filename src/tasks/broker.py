from taskiq import TaskiqEvents, TaskiqState
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from src.core.config import settings

# Налаштування backend для збереження результатів виконання задач
result_backend = RedisAsyncResultBackend(
    redis_url=settings.redis_url,
)

# Налаштування основного брокера завдань
broker = ListQueueBroker(
    url=settings.redis_url,
    result_backend=result_backend,
)


# Ініціалізація ресурсів при старті воркера
@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_broker(state: TaskiqState) -> None:
    """Виконується при запуску worker-процесу."""
    pass  # Тут можна зберегти з'єднання з БД, наприклад: state.db_pool = ...


# Закриття ресурсів при зупинці воркера
@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown_broker(state: TaskiqState) -> None:
    """Виконується при зупинці worker-процесу."""
    pass  # Тут закриваємо з'єднання
