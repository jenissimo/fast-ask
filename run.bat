@echo off
echo FastAsk - запуск приложения...

:: Проверяем наличие .env файла
if not exist .env (
    echo .env файл не найден. Копируем из env-example.txt...
    copy env-example.txt .env
)

:: Активируем виртуальное окружение
call venv\Scripts\activate.bat

:: Запускаем приложение
echo Запуск приложения...
python src\main.py