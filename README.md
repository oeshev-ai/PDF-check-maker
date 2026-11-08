# Генератор PDF-чеков

> CLI-утилита, которая из CSV и HTML-шаблона собирает отдельные PDF-чеки с кириллицей через WeasyPrint.

## Проблема

Чеки и акты часто собирают вручную: копируют строки из таблицы в Word или HTML, затем печатают в PDF. На Windows и macOS легко «ломается» кириллица и вёрстка таблиц, а длинные названия товаров разъезжают строки. На пачке документов это отнимает время и даёт риск опечаток и разного оформления.

## Решение

Интерактивный Python-скрипт: выбираете CSV и шаблон, указываете нужные строки — данные подставляются в HTML, WeasyPrint собирает PDF, файлы сразу открываются в системе. Единый шаблон и CSS (таблицы, перенос длинных строк, шрифт) дают одинаковый вид документов. Стек минимальный: стандартная библиотека Python плюс WeasyPrint.

## Что внутри

- Технологии: Python 3.11, WeasyPrint, `csv` / `pathlib` / `subprocess`, HTML/CSS
- Архитектура: CSV → подстановка плейсхолдеров (`str.replace`) → HTML → PDF → открытие через `os.startfile` / `open`
- Запуск: локально через `run.bat` / `run.sh` (venv поднимается автоматически); Windows и macOS; шрифты Roboto / Liberation Sans из `fonts/`

## Как запустить

```bash
git clone https://github.com/oeshev-ai/PDF_generator.git
cd PDF_generator
```

**Windows** — двойной клик по `run.bat` или в терминале:

```bat
run.bat
```

**macOS / Linux:**

```bash
chmod +x run.sh
./run.sh
```

Скрипт сам создаст `venv`, поставит зависимости и запустит генератор.

Положите CSV в `data/`, HTML-шаблоны — в `templates/`. Нужен установленный Python 3.10+. На Windows для WeasyPrint нужен [GTK3 Runtime](https://github.com/nicklasb/gtk3-windows/releases); на macOS: `brew install pango cairo gdk-pixbuf libffi`. Подробности — в [документации WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html). Для корректной кириллицы добавьте `Roboto-Regular.ttf` в `fonts/`.

## Результат

- Пакет чеков из CSV за один прогон вместо ручной сборки каждого файла
- Стабильная кириллица и единый вид таблиц в PDF
- Выбор записей (все / диапазон / список) без правки скрипта

## Контакт

Telegram: [@OEShevchenko](https://t.me/OEShevchenko)  
Email: oeshevip@yandex.ru
