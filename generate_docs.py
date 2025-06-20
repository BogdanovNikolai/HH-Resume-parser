"""
Скрипт для генерации README.md на основе заголовочных докстрингов всех .py файлов в проекте.

Игнорируемые директории:
    - .venv
    - __pycache__
    - .git
    - .env
    - migrations (если есть)
"""

import os
from pathlib import Path
import re
from typing import Optional


# Список директорий, которые нужно игнорировать
IGNORED_DIRS = {
    ".venv", "__pycache__", ".git", ".env", "migrations", "__pycache__", ".pytest_cache", "alembic"
}


def extract_module_docstring(file_path: str) -> Optional[str]:
    """
    Извлекает докстринг из начала указанного Python-файла.

    Args:
        file_path (str): путь к файлу.

    Returns:
        Optional[str]: содержимое докстринга или None, если не найдено.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Регулярное выражение для поиска докстринга в начале файла
        docstring_match = re.match(r'^\s*"""(.*?)"""', content, re.DOTALL)
        if docstring_match:
            return docstring_match.group(1).strip()
        return "Нет описания."
    except Exception as e:
        print(f"[ERROR] Ошибка при чтении {file_path}: {e}")
        return "Ошибка при чтении файла."


def is_ignored_dir(path: str) -> bool:
    """
    Проверяет, находится ли путь в списке игнорируемых директорий.

    Args:
        path (str): относительный путь директории.

    Returns:
        bool: True, если директория должна быть проигнорирована.
    """
    parts = Path(path).parts
    for part in parts:
        if part in IGNORED_DIRS:
            return True
    return False


def generate_project_overview(project_root: str = ".", output_file: str = "README.md"):
    """
    Генерирует общий файл документации проекта на основе докстрингов модулей.

    Args:
        project_root (str): корень проекта.
        output_file (str): имя выходного файла.
    """
    project_root = Path(project_root)

    files_with_docs = []

    for root, dirs, files in os.walk(project_root):
        # Удаляем игнорируемые директории из обхода
        dirs[:] = [d for d in dirs if not is_ignored_dir(str(Path(root) / d))]

        for file in files:
            if file.endswith(".py") and file != "__pycache__":
                file_path = Path(root) / file
                rel_path = file_path.relative_to(project_root)
                docstring = extract_module_docstring(file_path)

                files_with_docs.append((rel_path, docstring))

    # === Формируем README.md ===
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Документация проекта\n\n")
        f.write("## Оглавление\n\n")

        # Оглавление
        for rel_path, _ in files_with_docs:
            anchor = str(rel_path).replace("/", "_").replace(".", "_")
            f.write(f"- [{rel_path}]#{anchor}\n")

        f.write("\n---\n\n")

        # Содержание
        for rel_path, docstring in files_with_docs:
            anchor = str(rel_path).replace("/", "_").replace(".", "_")
            f.write(f"## {rel_path}\n")
            f.write(f"<a name='{anchor}'></a>\n")
            f.write(f"{docstring}\n\n")
            f.write("---\n\n")

    print(f"[INFO] Документация успешно сохранена в {output_file}")


if __name__ == "__main__":
    PROJECT_ROOT = "."  # Можно изменить на конкретную папку с кодом
    OUTPUT_FILE = "README.md"

    generate_project_overview(PROJECT_ROOT, OUTPUT_FILE)