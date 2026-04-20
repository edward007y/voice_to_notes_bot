import runpy
import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.main import main

# ==========================================
# ТЕСТИ ДЛЯ src.bot.main
# ==========================================


@pytest.mark.asyncio
@patch("src.bot.main.Dispatcher")
@patch("src.bot.main.Bot")
async def test_main_execution(mock_bot_class, mock_dp_class):
    """Семантична перевірка ініціалізації бота та запуску polling."""
    # Імітація об'єктів
    mock_bot_instance = AsyncMock()
    mock_bot_class.return_value = mock_bot_instance

    mock_dp_instance = MagicMock()
    mock_dp_instance.start_polling = AsyncMock()
    mock_dp_class.return_value = mock_dp_instance

    # Виклик оркестратора
    await main()

    # Перевірки згідно з логікою main()
    mock_bot_class.assert_called_once()
    mock_dp_class.assert_called_once()

    # Має бути підключено 2 роутери (commands та voice)
    assert mock_dp_instance.include_router.call_count == 2

    # Видалення webhook перед запуском
    mock_bot_instance.delete_webhook.assert_called_once_with(drop_pending_updates=True)

    # Запуск процесу polling
    mock_dp_instance.start_polling.assert_called_once_with(mock_bot_instance)


@patch("asyncio.run")
def test_main_module_script_execution(mock_asyncio_run):
    """
    Семантична перевірка блоку if __name__ == "__main__":.
    Використовуємо runpy та коректно закриваємо корутину.
    """
    with warnings.catch_warnings():
        # Глушимо системні попередження від runpy
        warnings.simplefilter("ignore")
        runpy.run_module("src.bot.main", run_name="__main__")

    # Згідно з логікою, asyncio.run має бути викликаний
    mock_asyncio_run.assert_called_once()

    # Витягуємо реальну корутину з аргументів виклику моку та закриваємо її
    # Це семантично усуває помилку "coroutine was never awaited"
    coro = mock_asyncio_run.call_args[0][0]
    coro.close()
