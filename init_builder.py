from pathlib import Path


def build_init_files() -> None:
    """Створює відсутні файли __init__.py для коректної структури пакетів."""
    packages = [
        "src",
        "src/bot",
        "src/bot/handlers",
        "src/bot/middlewares",
        "src/tasks",
        "src/services",
        "src/core",
        "tests",
    ]

    for pkg in packages:
        path = Path(pkg)
        path.mkdir(parents=True, exist_ok=True)
        init_file = path / "__init__.py"

        if not init_file.exists():
            init_file.write_text("", encoding="utf-8")
            print(f"Created: {init_file}")
        else:
            print(f"Already exists: {init_file}")


if __name__ == "__main__":
    build_init_files()
