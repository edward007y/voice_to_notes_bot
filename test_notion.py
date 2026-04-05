import asyncio

from src.services.notion import create_notion_page


async def main():
    print("Готуємо тестові дані...")

    # Імітуємо результат від GPT
    test_summary = "Це тестове резюме. Ми перевіряємо, чи успішно наш бот може підключатися до бази даних Notion та створювати структуровані сторінки з базовими блоками тексту."
    test_action_items = [
        "Перевірити, чи з'явилася сторінка в Notion",
        "Переконатися, що чекліст відображається коректно",
        "Видалити цей тестовий файл після перевірки",
    ]

    print("Відправляємо запит до Notion API...")
    try:
        page_url = await create_notion_page(test_summary, test_action_items)
        print("\n🎉 УСПІХ!")
        print(f"Твоя сторінка створена за посиланням: {page_url}")
    except Exception as e:
        print(f"\n❌ ПОМИЛКА: {e}")


if __name__ == "__main__":
    asyncio.run(main())
