#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Ошибка: Python не найден. Установите Python 3.10+."
  exit 1
fi

if [ ! -x "venv/bin/python" ]; then
  echo "Создаю виртуальное окружение..."
  "$PY" -m venv venv
fi

echo "Проверяю зависимости..."
venv/bin/python -m pip install -q -r requirements.txt

echo
exec venv/bin/python generate_receipts.py
