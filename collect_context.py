import os

OUTPUT_FILE = "project_context.txt"
INCLUDE_EXTENSIONS = (".py", ".ftl", ".yaml", ".ini")
INCLUDE_FILES = (
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "alembic.ini",
    ".gitignore",
)
EXCLUDE_DIRS = {
    "collect_context.py",
    "venv",
    ".venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    "env",
    "dist",
    "build",
    ".idea",
    "project_context.txt",
    ".vscode",
    "test_results.txt",
    "parser_test.txt",
}


def generate_tree(startpath):
    tree_str = "PROJECT STRUCTURE:\n"
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        level = root.replace(startpath, "").count(os.sep)
        indent = " " * 4 * level
        tree_str += f"{indent}{os.path.basename(root)}/\n"
        subindent = " " * 4 * (level + 1)
        for f in files:
            if f.endswith(INCLUDE_EXTENSIONS) or f in INCLUDE_FILES:
                tree_str += f"{subindent}{f}\n"
    return tree_str


def collect_project_data(root_path="."):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f_out:
        # Спочатку записуємо структуру проекту
        f_out.write(generate_tree(root_path))
        f_out.write("\n" + "=" * 50 + "\n")
        f_out.write("FILE CONTENTS BEGIN HERE\n")
        f_out.write("=" * 50 + "\n")

        for root, dirs, files in os.walk(root_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                if file.endswith(INCLUDE_EXTENSIONS) or file in INCLUDE_FILES:
                    if file == os.path.basename(__file__) or file == OUTPUT_FILE:
                        continue

                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, root_path)

                    f_out.write(f"\n--- FILE: {relative_path} ---\n")
                    try:
                        with open(full_path, "r", encoding="utf-8") as f_in:
                            f_out.write(f_in.read())
                    except Exception as e:
                        f_out.write(f"[Error reading file: {e}]\n")
                    f_out.write("\n")

    print(f"Готово! Файл створено: {os.path.abspath(OUTPUT_FILE)}")


if __name__ == "__main__":
    collect_project_data()
