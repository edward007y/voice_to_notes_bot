from unittest.mock import AsyncMock, MagicMock

import pytest
from taskiq import TaskiqState

from src.tasks.broker import shutdown_broker, startup_broker


@pytest.mark.asyncio
async def test_startup_broker():
    """Семантична перевірка ініціалізації бота під час запуску воркера."""
    state = TaskiqState()

    await startup_broker(state)  # type: ignore

    # Перевіряємо, що бот був створений і доданий до стану
    assert hasattr(state, "bot")
    assert state.bot is not None


@pytest.mark.asyncio
async def test_shutdown_broker():
    """Перевірка закриття сесії бота під час зупинки воркера."""
    state = TaskiqState()
    state.bot = AsyncMock()
    state.bot.session.close = AsyncMock()

    await shutdown_broker(state)  # type: ignore

    # Перевіряємо, що сесія бота закрита
    state.bot.session.close.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_broker_no_bot():
    """Перевірка зупинки, якщо бот не був ініціалізований (early return)."""
    state = TaskiqState()

    # Згідно з логікою, помилки не повинно бути
    await shutdown_broker(state)  # type: ignore
