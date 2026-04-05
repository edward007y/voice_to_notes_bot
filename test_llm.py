import asyncio

from src.services.openai_llm import summarize_text


async def main():
    sample_text = "Привіт! Коротше, по проєкту редизайну. Нам треба до п'ятниці зібрати фідбек від клієнта. Також нагадай мені написати Івану щодо договорів, і давай заплануємо зідзвон на понеділок о 10 ранку."

    print("Відправляємо текст до OpenAI...")
    try:
        result = await summarize_text(sample_text)
        print("\n--- РЕЗУЛЬТАТ ---")
        print(f"SUMMARY:\n{result.summary}")
        print("\nACTION ITEMS:")
        if result.action_items:
            for item in result.action_items:
                print(f"- {item}")
        else:
            print("Задач не знайдено.")
    except Exception as e:
        print(f"ПОМИЛКА: {e}")


if __name__ == "__main__":
    asyncio.run(main())
