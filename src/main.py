#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAsk - быстрый запуск запросов к LLM (OpenAI API)
"""

import sys
import os
import signal
import logging
from pathlib import Path
from dotenv import load_dotenv

# Добавляем корень проекта в PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

# Загружаем .env файл
env_path = root_dir / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    print(f"Файл .env не найден, создаем с дефолтными настройками по пути: {env_path}")
    with open(env_path, 'w', encoding='utf-8') as f:
        with open(root_dir / '.env.example', 'r', encoding='utf-8') as example:
            f.write(example.read())
    load_dotenv(dotenv_path=env_path)

from src.app import Application

# Глобальная переменная для хранения экземпляра приложения
app_instance = None

def signal_handler(sig, frame):
    """Обработчик сигнала прерывания (CTRL+C)"""
    print("\nПолучен сигнал прерывания (CTRL+C). Завершаем работу...")
    
    # Если приложение запущено, корректно завершаем его
    if app_instance:
        logging.info("Завершение работы приложения...")
        
        # Остановка хоткей-менеджера
        if hasattr(app_instance, 'hotkey_manager'):
            app_instance.hotkey_manager.stop()
        
        # Завершаем приложение
        app_instance.quit()
    
    # Принудительно выходим
    sys.exit(0)

def main():
    """Main entry point for the application"""
    global app_instance
    
    # Устанавливаем обработчик сигнала
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Создаем экземпляр приложения
    app_instance = Application(sys.argv)
    
    # Запускаем приложение
    return app_instance.exec()

if __name__ == "__main__":
    sys.exit(main()) 