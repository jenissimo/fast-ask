#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Основной класс приложения FastAsk
"""

import os
import sys
import logging
import asyncio
import threading
from pathlib import Path
from functools import partial
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QSettings, pyqtSlot, QThread, QObject, pyqtSignal

from src.ui.main_window import MainWindow
from src.ui.modern_window import ModernWindow
from src.models.db_manager import DatabaseManager
from src.utils.hotkey_manager import HotkeyManager
from src.utils.screenshot import ScreenshotManager
from src.api.openai_client import OpenAIClient

class APIWorker(QObject):
    """Рабочий поток для работы с API в фоне"""
    
    # Сигнал о получении ответа
    response_received = pyqtSignal(str)
    
    # Сигнал о получении части ответа
    response_chunk = pyqtSignal(str)
    
    # Сигнал о завершении работы
    finished = pyqtSignal()
    
    # Сигнал об окончании генерации (с полным ответом)
    generation_complete = pyqtSignal(str)
    
    def __init__(self, client, messages, temperature, max_tokens, stream=True):
        """Инициализация рабочего потока
        
        Args:
            client: Экземпляр OpenAIClient
            messages: Список сообщений
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            stream: Использовать потоковую генерацию
        """
        super().__init__()
        self.client = client
        self.messages = messages
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = stream
        self.full_response = ""  # Для накопления полного ответа
    
    def run(self):
        """Запуск обработки запроса"""
        response = self.client.create_chat_completion(
            messages=self.messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=self.stream,
            on_chunk=self.on_chunk if self.stream else None,
            on_finish=self.on_finish if self.stream else None
        )
        
        if not self.stream:
            # Если не потоковая генерация, эмитим весь ответ сразу
            self.response_received.emit(response)
        
        self.finished.emit()
    
    def on_chunk(self, chunk):
        """Обработка получения части ответа"""
        self.full_response += chunk
        self.response_chunk.emit(chunk)
    
    def on_finish(self):
        """Обработка завершения генерации"""
        # Эмитим сигнал с полным ответом
        self.generation_complete.emit(self.full_response)

class Application(QApplication):
    """Основной класс приложения FastAsk"""

    def __init__(self, argv):
        """Инициализация приложения"""
        super().__init__(argv)
        
        # Настройка логгирования
        self._setup_logging()
        
        # Инициализация компонентов
        self._setup_settings()
        self._setup_database()
        self._setup_api_client()
        self._setup_screenshot_manager()
        self._setup_ui()
        self._setup_hotkeys()
        
        # Текущий рабочий поток для API запросов
        self.api_worker = None
        self.api_thread = None
        
        logging.info("Приложение FastAsk инициализировано")
    
    def _setup_logging(self):
        """Настройка логгирования"""
        log_level = os.getenv("LOG_LEVEL", "INFO")
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            numeric_level = logging.INFO
        
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _setup_settings(self):
        """Инициализация настроек приложения"""
        self.settings = QSettings("FastAsk", "FastAsk")
        
        # Установка темы приложения
        theme = os.getenv("THEME", "dark")
        self.set_theme(theme)
    
    def _setup_database(self):
        """Инициализация базы данных"""
        db_path = os.getenv("DB_PATH", "data/history.db")
        # Создаем папку, если не существует
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_manager = DatabaseManager(db_path)
    
    def _setup_api_client(self):
        """Инициализация клиента API"""
        self.api_client = OpenAIClient()
    
    def _setup_screenshot_manager(self):
        """Инициализация менеджера скриншотов"""
        screenshots_dir = os.getenv("SCREENSHOTS_DIR", "data/screenshots")
        Path(screenshots_dir).mkdir(parents=True, exist_ok=True)
        
        self.screenshot_manager = ScreenshotManager(screenshots_dir)
    
    def _setup_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Используем современный интерфейс
        use_modern_ui = os.getenv("USE_MODERN_UI", "true").lower() == "true"
        
        if use_modern_ui:
            self.main_window = ModernWindow(self)
        else:
            self.main_window = MainWindow(self)
        
        # Подключаем сигналы
        self.main_window.send_request.connect(self.on_send_request)
        self.main_window.stop_generation.connect(self.on_stop_generation)
        self.screenshot_manager.screenshot_captured.connect(
            self.main_window.on_screenshot_captured
        )
        
        # Показываем окно сразу при запуске
        self.main_window.show()
        self.main_window.activateWindow()
        self.main_window.raise_()
    
    def _setup_hotkeys(self):
        """Инициализация глобальных горячих клавиш"""
        self.hotkey_manager = HotkeyManager()
        
        # Регистрируем хоткеи
        app_hotkey = os.getenv("APP_HOTKEY", "ctrl+shift+space")
        screenshot_hotkey = os.getenv("SCREENSHOT_HOTKEY", "ctrl+shift+s")
        
        self.hotkey_manager.register_hotkey(
            app_hotkey, 
            self.main_window.show_hide
        )
        
        self.hotkey_manager.register_hotkey(
            screenshot_hotkey,
            self.screenshot_manager.capture
        )
    
    @pyqtSlot(str, object)
    def on_send_request(self, query, screenshot=None):
        """Обработка отправки запроса к API
        
        Args:
            query (str): Текст запроса
            screenshot (Path, optional): Путь к скриншоту
        """
        # Если уже идет генерация, ничего не делаем
        if self.api_thread and self.api_thread.isRunning():
            return
        
        # Получаем параметры генерации из настроек
        temperature = float(os.getenv("TEMPERATURE", "0.7"))
        max_tokens = int(os.getenv("MAX_TOKENS", "1000"))
        system_prompt = os.getenv("SYSTEM_PROMPT", "Ты полезный ассистент. Отвечай кратко и по делу.")
        model = os.getenv("OPENAI_MODEL", "google/gemini-2.5-flash")
        
        # Используем одну и ту же модель для всех запросов (Gemini 2.5 Flash мультимодальная)
        self.api_client.model = model
        
        # Создаем сообщения для отправки
        messages = []
        
        # Добавляем системное сообщение
        messages.append(self.api_client.create_system_message(system_prompt))
        
        # Если есть скриншот, добавляем его к запросу
        if screenshot:
            # Создаем сообщение с изображением
            user_message = {
                "role": "user",
                "content": self.api_client.create_image_message(query, screenshot)
            }
            messages.append(user_message)
            
            logging.info(f"Отправка запроса с изображением, используя модель: {model}")
        else:
            # Обычный текстовый запрос
            messages.append(self.api_client.create_user_message(query))
            
            logging.info(f"Отправка текстового запроса, используя модель: {model}")
        
        # Создаем рабочий поток
        self.api_worker = APIWorker(
            client=self.api_client,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True  # Всегда используем потоковую генерацию
        )
        
        # Создаем и настраиваем поток
        self.api_thread = QThread()
        self.api_worker.moveToThread(self.api_thread)
        
        # Подключаем сигналы
        self.api_thread.started.connect(self.api_worker.run)
        self.api_worker.finished.connect(self.api_thread.quit)
        self.api_worker.finished.connect(self.api_worker.deleteLater)
        self.api_thread.finished.connect(self.api_thread.deleteLater)
        self.api_thread.finished.connect(self._reset_api_objects)
        
        # Подключаем сигналы к главному окну
        self.api_worker.response_received.connect(self.main_window.on_response_received)
        self.api_worker.response_chunk.connect(self.main_window.on_response_chunk)
        self.api_worker.generation_complete.connect(self.main_window.on_generation_complete)
        
        # Запускаем поток
        self.api_thread.start()
        
        # Сохраняем запрос в историю
        history_id = self.db_manager.add_history_item(
            query=query,
            response="[Генерация...]",
            has_screenshot=bool(screenshot),
            screenshot_path=str(screenshot) if screenshot else None,
            model_name=self.api_client.model,
            metadata={
                "temperature": temperature,
                "max_tokens": max_tokens
            }
        )
        
        # Сохраняем ID для последующего обновления
        self.current_history_id = history_id
    
    def _reset_api_objects(self):
        """Сброс ссылок на API объекты после завершения работы потока"""
        logging.debug("Очистка ссылок на API объекты")
        
        # Для безопасности обрабатываем любые исключения, так как объект мог быть уже удален
        if self.api_worker:
            try:
                # Пытаемся отключить сигналы, но обрабатываем все возможные исключения
                try:
                    self.api_worker.response_received.disconnect()
                except Exception:
                    pass
                    
                try:
                    self.api_worker.response_chunk.disconnect()
                except Exception:
                    pass
                    
                try:
                    self.api_worker.generation_complete.disconnect()
                except Exception:
                    pass
                    
                try:
                    self.api_worker.finished.disconnect()
                except Exception:
                    pass
            except Exception as e:
                logging.debug(f"Ошибка при отключении сигналов: {e}")
            
        # Очищаем ссылки на объекты
        self.api_worker = None
        self.api_thread = None
    
    @pyqtSlot()
    def on_stop_generation(self):
        """Обработка прерывания генерации ответа"""
        if self.api_client and self.api_worker:
            # Логируем событие остановки
            logging.info("Остановка генерации пользователем")
            
            # Отменяем текущую генерацию в клиенте
            self.api_client.cancel()
            
            # Обновляем запись в истории с информацией о прерывании
            if hasattr(self, 'current_history_id'):
                try:
                    # Получаем текущий ответ из UI
                    partial_response = self.main_window.current_response if hasattr(self.main_window, 'current_response') else "[Генерация прервана]"
                    
                    # Добавляем метку о прерывании
                    if not partial_response.endswith("*Генерация прервана пользователем*"):
                        partial_response += "\n\n*Генерация прервана пользователем*"
                    
                    # Обновляем запись в БД
                    self.db_manager.update_history_response(
                        self.current_history_id,
                        partial_response
                    )
                except Exception as e:
                    logging.error(f"Ошибка при обновлении истории после остановки: {e}")
            
            # Для безопасности сбрасываем состояние UI
            self.main_window._reset_generation_state()
    
    def set_theme(self, theme_name):
        """Установка темы приложения"""
        if theme_name.lower() == "dark":
            self.setStyle("Fusion")
            palette = self.palette()
            palette.setColor(palette.ColorRole.Window, Qt.GlobalColor.darkGray)
            palette.setColor(palette.ColorRole.WindowText, Qt.GlobalColor.white)
            palette.setColor(palette.ColorRole.Base, Qt.GlobalColor.darkGray)
            palette.setColor(palette.ColorRole.AlternateBase, Qt.GlobalColor.gray)
            palette.setColor(palette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
            palette.setColor(palette.ColorRole.ToolTipText, Qt.GlobalColor.white)
            palette.setColor(palette.ColorRole.Text, Qt.GlobalColor.white)
            palette.setColor(palette.ColorRole.Button, Qt.GlobalColor.darkGray)
            palette.setColor(palette.ColorRole.ButtonText, Qt.GlobalColor.white)
            palette.setColor(palette.ColorRole.Link, Qt.GlobalColor.blue)
            palette.setColor(palette.ColorRole.Highlight, Qt.GlobalColor.blue)
            palette.setColor(palette.ColorRole.HighlightedText, Qt.GlobalColor.black)
            self.setPalette(palette)
        else:
            # Light theme - используем системную
            self.setStyle("Fusion")
            self.setPalette(self.style().standardPalette()) 