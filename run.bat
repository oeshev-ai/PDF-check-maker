@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
    where py >nul 2>&1
    if errorlevel 1 (
        echo Ошибка: Python не найден. Установите Python 3.10+ с https://www.python.org/downloads/
        echo При установке отметьте "Add python.exe to PATH".
        pause
        exit /b 1
    )
    set "PY=py -3"
) else (
    set "PY=python"
)

if not exist "venv\Scripts\python.exe" (
    echo Создаю виртуальное окружение...
    %PY% -m venv venv
    if errorlevel 1 (
        echo Ошибка: не удалось создать venv.
        pause
        exit /b 1
    )
)

echo Проверяю зависимости...
"venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo Ошибка: не удалось установить зависимости.
    pause
    exit /b 1
)

echo.
"venv\Scripts\python.exe" generate_receipts.py
set "EXITCODE=%ERRORLEVEL%"

echo.
pause
exit /b %EXITCODE%
