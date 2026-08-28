#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор чеков: CSV → HTML → PDF (WeasyPrint).
Интерактивный выбор файлов и записей. Windows и macOS.
"""

from __future__ import annotations

import csv
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from weasyprint import HTML, CSS
except ImportError:
    print(
        "Ошибка: библиотека WeasyPrint не установлена.\n"
        "Установите её командой: pip install weasyprint"
    )
    sys.exit(1)
except OSError as exc:
    print(
        "Ошибка: WeasyPrint не может загрузить системные библиотеки.\n"
        f"Подробности: {exc}\n\n"
        "Windows: установите GTK3 Runtime — "
        "https://github.com/nicklasb/gtk3-windows/releases\n"
        "macOS: brew install pango cairo gdk-pixbuf libffi\n"
        "Документация: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html"
    )
    sys.exit(1)


# --- Настраиваемые пути ---
DATA_DIR = Path("./data")
TEMPLATES_DIR = Path("./templates")
OUTPUT_DIR = Path("./output")
HTML_OUTPUT_DIR = OUTPUT_DIR / "html"
FONTS_DIR = Path("./fonts")
PREVIEW_ROWS = 5

# Плейсхолдеры в шаблоне (ключ CSV → имя плейсхолдера без {{ }})
PLACEHOLDER_ALIASES = {
    "order_id": ["order_id", "номер", "number", "id", "№", "no"],
    "date": ["date", "дата"],
    "items": ["items", "товары", "products", "goods"],
    "total": ["total", "сумма", "amount", "итого"],
}


def ensure_directories() -> None:
    """Создаёт рабочие папки, если их нет."""
    created = []
    for directory in (DATA_DIR, TEMPLATES_DIR, OUTPUT_DIR, HTML_OUTPUT_DIR, FONTS_DIR):
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(str(directory))
    if created:
        print("Созданы отсутствующие папки:")
        for path in created:
            print(f"  • {path}")
        print(
            "\nПоместите CSV-файлы в папку data/, HTML-шаблоны — в templates/.\n"
            "Для корректной кириллицы положите шрифт Roboto или Liberation Sans в fonts/.\n"
        )


def list_files(directory: Path, pattern: str, label: str) -> list[Path]:
    """Возвращает отсортированный список файлов по маске."""
    if not directory.is_dir():
        return []
    files = sorted(Path(p) for p in glob.glob(str(directory / pattern)))
    return [f for f in files if f.is_file()]


def choose_from_list(items: list[Path], prompt: str) -> Path | None:
    """Интерактивный выбор файла по номеру или имени."""
    if not items:
        print(f"В каталоге не найдено файлов ({prompt}).")
        return None

    print(f"\n{prompt}:")
    for i, item in enumerate(items, start=1):
        print(f"  {i}. {item.name}")

    while True:
        raw = input("\nВведите номер или имя файла (Enter — отмена): ").strip()
        if not raw:
            print("Выбор отменён.")
            return None

        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(items):
                return items[idx - 1]
            print(f"Ошибка: номер должен быть от 1 до {len(items)}.")
            continue

        # Поиск по имени (полному или частичному)
        matches = [f for f in items if raw.lower() in f.name.lower()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            print("Найдено несколько совпадений, уточните имя:")
            for m in matches:
                print(f"  • {m.name}")
            continue

        print(f"Файл «{raw}» не найден. Попробуйте снова.")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Читает CSV через DictReader, возвращает заголовки и строки."""
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("CSV-файл пуст или не содержит заголовков.")
        fieldnames = list(reader.fieldnames)
        for row in reader:
            rows.append({k: (v or "").strip() for k, v in row.items()})
    if not rows:
        raise ValueError("CSV-файл не содержит записей (только заголовки).")
    return fieldnames, rows


def preview_rows(rows: list[dict[str, str]], fieldnames: list[str], count: int = PREVIEW_ROWS) -> None:
    """Показывает первые строки CSV."""
    print(f"\nВсего записей: {len(rows)}")
    print(f"Первые {min(count, len(rows))} записей:\n")
    header = " | ".join(fieldnames)
    print(header)
    print("-" * min(len(header), 80))
    for row in rows[:count]:
        print(" | ".join(row.get(col, "") for col in fieldnames))


def parse_row_selection(raw: str, total: int) -> list[int]:
    """
    Разбирает выбор строк: пусто → все; «3»; «3-7»; «1,5,9».
    Возвращает список индексов (0-based).
    """
    if not raw.strip():
        return list(range(total))

    indices: set[int] = set()
    parts = [p.strip() for p in raw.split(",") if p.strip()]

    for part in parts:
        range_match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start < 1 or end < 1 or start > end:
                raise ValueError(f"Некорректный диапазон: «{part}».")
            if end > total:
                raise ValueError(
                    f"Диапазон «{part}» выходит за пределы (максимум {total})."
                )
            indices.update(range(start - 1, end))
            continue

        if part.isdigit():
            num = int(part)
            if num < 1 or num > total:
                raise ValueError(
                    f"Номер строки {num} вне диапазона 1–{total}."
                )
            indices.add(num - 1)
            continue

        raise ValueError(
            f"Не удалось разобрать «{part}». "
            "Используйте: номер, диапазон (3-7) или список (1,5,9)."
        )

    return sorted(indices)


def ask_row_selection(total: int) -> list[int]:
    """Запрашивает у пользователя, какие записи обрабатывать."""
    print(
        "\nВыберите записи для обработки:\n"
        "  • Enter — все записи\n"
        "  • номер — одна запись (например: 3)\n"
        "  • диапазон — например: 3-7\n"
        "  • список — например: 1,5,9"
    )
    while True:
        raw = input("\nВаш выбор: ").strip()
        try:
            indices = parse_row_selection(raw, total)
            if not indices:
                print("Не выбрано ни одной записи.")
                continue
            labels = [str(i + 1) for i in indices]
            print(f"Будут обработаны записи: {', '.join(labels)}")
            return indices
        except ValueError as exc:
            print(f"Ошибка: {exc}")


def find_column(fieldnames: list[str], aliases: list[str]) -> str | None:
    """Ищет колонку CSV по списку возможных имён (без учёта регистра)."""
    normalized = {name.strip().lower(): name for name in fieldnames}
    for alias in aliases:
        key = alias.lower()
        if key in normalized:
            return normalized[key]
    return None


def build_replacements(row: dict[str, str], fieldnames: list[str]) -> dict[str, str]:
    """Формирует словарь плейсхолдер → значение."""
    replacements: dict[str, str] = {}

    for placeholder, aliases in PLACEHOLDER_ALIASES.items():
        col = find_column(fieldnames, aliases)
        if col:
            replacements[placeholder] = row.get(col, "")

    # Все остальные колонки — по имени колонки как плейсхолдер
    for col in fieldnames:
        key = col.strip()
        if key and key not in replacements:
            replacements[key] = row.get(col, "")

    return replacements


def apply_template(template: str, replacements: dict[str, str]) -> str:
    """Подставляет {{ key }} в HTML-шаблон."""
    result = template
    for key, value in replacements.items():
        result = result.replace(f"{{{{ {key} }}}}", value)
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def find_font_file() -> Path | None:
    """Ищет Roboto или Liberation Sans в fonts/ и системных путях."""
    candidates = [
        FONTS_DIR / "Roboto-Regular.ttf",
        FONTS_DIR / "Roboto.ttf",
        FONTS_DIR / "LiberationSans-Regular.ttf",
        FONTS_DIR / "LiberationSans-Regular.otf",
    ]
    if sys.platform == "win32":
        candidates.extend([
            Path(r"C:\Windows\Fonts\arial.ttf"),
            Path(r"C:\Windows\Fonts\arialuni.ttf"),
        ])
    elif sys.platform == "darwin":
        candidates.extend([
            Path("/Library/Fonts/Arial Unicode.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            Path("/Library/Fonts/Arial.ttf"),
        ])

    for path in candidates:
        if path.is_file():
            return path.resolve()
    return None


def build_pdf_css(font_path: Path | None) -> CSS:
    """CSS для кириллицы, таблиц и переноса длинных строк."""
    font_face = ""
    font_family = "sans-serif"
    if font_path:
        uri = font_path.as_uri()
        font_face = f"""
@font-face {{
    font-family: 'ReceiptFont';
    src: url('{uri}');
    font-weight: normal;
    font-style: normal;
}}
"""
        font_family = "'ReceiptFont', 'Roboto', 'Liberation Sans', sans-serif"

    css_text = f"""
{font_face}
body {{
    font-family: {font_family};
    font-size: 12pt;
    color: #222;
    margin: 20mm;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    table-layout: fixed;
}}
th, td {{
    border: 1px solid #333;
    padding: 8px 10px;
    text-align: center;
    vertical-align: middle;
    word-wrap: break-word;
    overflow-wrap: break-word;
    word-break: break-word;
    hyphens: auto;
}}
th {{
    background-color: #f0f0f0;
    font-weight: bold;
}}
h1, h2, h3 {{
    text-align: center;
}}
.receipt-meta {{
    margin-bottom: 1.5em;
}}
.receipt-meta p {{
    margin: 0.3em 0;
}}
.total {{
    font-size: 14pt;
    font-weight: bold;
    text-align: center;
    margin-top: 1em;
}}
"""
    return CSS(string=css_text)


def sanitize_filename(value: str, fallback: str) -> str:
    """Безопасное имя файла из значения колонки."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", value.strip())
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = cleaned[:80] if cleaned else fallback
    return cleaned or fallback


def make_output_basename(row: dict[str, str], fieldnames: list[str], row_index: int) -> str:
    """Осмысленное имя: receipt_<первая_колонка> или receipt_<номер>."""
    first_col = fieldnames[0] if fieldnames else None
    if first_col and row.get(first_col):
        slug = sanitize_filename(row[first_col], f"{row_index:03d}")
        return f"receipt_{slug}"
    return f"receipt_{row_index:03d}"


def open_pdf(path: Path) -> None:
    """Открывает PDF в системной программе (Windows / macOS / Linux)."""
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError as exc:
        print(f"  Предупреждение: не удалось открыть {path.name}: {exc}")


def load_template(path: Path) -> str:
    """Загружает HTML-шаблон."""
    return path.read_text(encoding="utf-8")


def generate_for_rows(
    rows: list[dict[str, str]],
    fieldnames: list[str],
    indices: list[int],
    template_text: str,
    font_path: Path | None,
) -> list[Path]:
    """Генерирует HTML и PDF для выбранных строк."""
    pdf_css = build_pdf_css(font_path)
    generated_pdfs: list[Path] = []

    for idx in indices:
        row = rows[idx]
        row_num = idx + 1
        basename = make_output_basename(row, fieldnames, row_num)
        html_path = HTML_OUTPUT_DIR / f"{basename}.html"
        pdf_path = OUTPUT_DIR / f"{basename}.pdf"

        replacements = build_replacements(row, fieldnames)
        html_content = apply_template(template_text, replacements)

        try:
            html_path.write_text(html_content, encoding="utf-8")
            HTML(string=html_content, base_url=str(html_path.parent)).write_pdf(
                str(pdf_path),
                stylesheets=[pdf_css],
            )
            print(f"  ✓ Запись {row_num}: {pdf_path.name}")
            generated_pdfs.append(pdf_path)
        except Exception as exc:
            print(f"  ✗ Запись {row_num}: ошибка — {exc}")

    return generated_pdfs


def main() -> int:
    print("=" * 60)
    print("  Генератор чеков CSV → HTML → PDF")
    print("=" * 60)

    ensure_directories()

    csv_files = list_files(DATA_DIR, "*.csv", "CSV")
    template_files = list_files(TEMPLATES_DIR, "*.html", "HTML")

    csv_path = choose_from_list(csv_files, "Найденные CSV-файлы")
    if csv_path is None:
        return 1

    template_path = choose_from_list(template_files, "Найденные HTML-шаблоны")
    if template_path is None:
        return 1

    try:
        fieldnames, rows = read_csv(csv_path)
    except (OSError, ValueError) as exc:
        print(f"Ошибка чтения CSV: {exc}")
        return 1

    preview_rows(rows, fieldnames)
    indices = ask_row_selection(len(rows))

    try:
        template_text = load_template(template_path)
    except OSError as exc:
        print(f"Ошибка чтения шаблона: {exc}")
        return 1

    font_path = find_font_file()
    if font_path:
        print(f"\nШрифт для PDF: {font_path.name}")
    else:
        print(
            "\nПредупреждение: шрифт Roboto/Liberation Sans не найден. "
            "Кириллица может отображаться некорректно.\n"
            "Поместите Roboto-Regular.ttf или LiberationSans-Regular.ttf в папку fonts/."
        )

    print(f"\nГенерация {len(indices)} файл(ов)...")
    pdfs = generate_for_rows(rows, fieldnames, indices, template_text, font_path)

    if not pdfs:
        print("\nНе создано ни одного PDF.")
        return 1

    print(f"\nГотово. PDF сохранены в: {OUTPUT_DIR.resolve()}")
    print("Открываю PDF...")
    for pdf in pdfs:
        open_pdf(pdf)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем.")
        sys.exit(130)
