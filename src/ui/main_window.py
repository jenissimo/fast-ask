#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Основное окно приложения FastAsk
"""

import os
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QProgressBar,
    QSplitter, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QKeySequence, QShortcut

class MainWindow(QMainWindow):
    """Основное окно приложения FastAsk"""
    
    # Сигнал для отправки запроса к API
    send_request = pyqtSignal(str, object)
    
    # Сигнал для прерывания генерации
    stop_generation = pyqtSignal()
    
    def __init__(self, app):
        """Инициализация основного окна приложения"""
        super().__init__()
        
        self.app = app
        self.screenshot = None
        
        # Настраиваем окно
        self._setup_window()
        
        # Инициализируем UI компоненты
        self._init_ui()
        
        # Подключаем сигналы
        self._connect_signals()
        
        # Состояние генерации ответа
        self.is_generating = False
        
        logging.info("Основное окно инициализировано")
    
    def _setup_window(self):
        """Настройка параметров окна"""
        self.setWindowTitle("FastAsk")
        self.setMinimumSize(600, 400)
        
        # Загружаем настройки позиции и размера
        geometry = self.app.settings.value("mainwindow/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # По умолчанию размещаем по центру экрана
            self.resize(800, 600)
            self.center_on_screen()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной лейаут
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Splitter для разделения запроса и ответа
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Верхняя часть - запрос
        query_frame = QFrame()
        query_layout = QVBoxLayout(query_frame)
        query_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок запроса
        query_title = QLabel("Запрос:")
        query_layout.addWidget(query_title)
        
        # Поле для ввода запроса
        self.query_input = QTextEdit()
        self.query_input.setPlaceholderText("Введите ваш запрос здесь...")
        self.query_input.setMinimumHeight(100)
        self.query_input.setAcceptRichText(False)
        query_layout.addWidget(self.query_input)
        
        # Панель с кнопками
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 5, 0, 0)
        
        # Блок информации о скриншоте
        self.screenshot_info = QLabel("Скриншот: нет")
        buttons_layout.addWidget(self.screenshot_info)
        
        # Распорка
        buttons_layout.addStretch(1)
        
        # Кнопка скриншота
        self.screenshot_button = QPushButton("Скриншот (Ctrl+Shift+S)")
        self.screenshot_button.clicked.connect(self._capture_screenshot)
        buttons_layout.addWidget(self.screenshot_button)
        
        # Кнопка отправки
        self.send_button = QPushButton("Отправить (Ctrl+Enter)")
        self.send_button.clicked.connect(self._on_send_clicked)
        buttons_layout.addWidget(self.send_button)
        
        query_layout.addLayout(buttons_layout)
        splitter.addWidget(query_frame)
        
        # Нижняя часть - ответ
        response_frame = QFrame()
        response_layout = QVBoxLayout(response_frame)
        response_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок ответа и статус
        header_layout = QHBoxLayout()
        response_title = QLabel("Ответ:")
        header_layout.addWidget(response_title)
        
        # Прогресс-бар для индикации генерации
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Бесконечный прогресс
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(100)
        header_layout.addWidget(self.progress_bar)
        
        # Распорка
        header_layout.addStretch(1)
        
        # Кнопка остановки генерации
        self.stop_button = QPushButton("Остановить")
        self.stop_button.setVisible(False)
        self.stop_button.clicked.connect(self._stop_generation)
        header_layout.addWidget(self.stop_button)
        
        response_layout.addLayout(header_layout)
        
        # Поле для отображения ответа
        self.response_output = QTextEdit()
        self.response_output.setReadOnly(True)
        self.response_output.setPlaceholderText("Здесь будет отображен ответ...")
        response_layout.addWidget(self.response_output)
        
        splitter.addWidget(response_frame)
        
        # Устанавливаем начальное соотношение размеров сплиттера
        splitter.setSizes([200, 400])
    
    def _connect_signals(self):
        """Подключение обработчиков сигналов"""
        # Горячая клавиша для отправки запроса
        self.send_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.send_shortcut.activated.connect(self._on_send_clicked)
        
        # Горячая клавиша для создания скриншота
        self.screenshot_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.screenshot_shortcut.activated.connect(self._capture_screenshot)
    
    def _on_send_clicked(self):
        """Обработка нажатия на кнопку отправки"""
        if self.is_generating:
            # Если генерация уже идет, ничего не делаем
            return
        
        query_text = self.query_input.toPlainText().strip()
        if not query_text:
            # Если запрос пустой, ничего не делаем
            return
        
        # Отправляем запрос (сигнал будет обработан в app.py)
        self.send_request.emit(query_text, self.screenshot)
        
        # Сбрасываем скриншот после отправки
        self.screenshot = None
        self.screenshot_info.setText("Скриншот: нет")
        
        # Включаем индикаторы загрузки
        self.progress_bar.setVisible(True)
        self.stop_button.setVisible(True)
        self.is_generating = True
    
    def _stop_generation(self):
        """Прерывание генерации ответа"""
        if self.is_generating:
            self.stop_generation.emit()
            self._reset_generation_state()
    
    def _reset_generation_state(self):
        """Сброс состояния генерации"""
        self.is_generating = False
        self.progress_bar.setVisible(False)
        self.stop_button.setVisible(False)
    
    def _capture_screenshot(self):
        """Запуск захвата скриншота"""
        # Скрываем окно перед захватом
        self.hide()
        # Небольшая задержка перед захватом скриншота
        QTimer.singleShot(500, self.app.screenshot_manager.capture)
    
    def on_screenshot_captured(self, screenshot):
        """Обработка захваченного скриншота"""
        # Показываем окно после захвата
        self.show()
        
        if screenshot is not None:
            self.screenshot = screenshot
            self.screenshot_info.setText("Скриншот: добавлен")
    
    def on_response_received(self, response):
        """Обработка полученного ответа"""
        self.response_output.setPlainText(response)
        self._reset_generation_state()
    
    def on_response_chunk(self, chunk):
        """Обработка части ответа (при потоковой генерации)"""
        current_text = self.response_output.toPlainText()
        self.response_output.setPlainText(current_text + chunk)
    
    def on_generation_complete(self, full_response):
        """Обработка завершения генерации"""
        # Устанавливаем полный ответ, если нужно
        if full_response and self.response_output.toPlainText() != full_response:
            self.response_output.setPlainText(full_response)
            
        # Скрываем индикаторы генерации
        self._reset_generation_state()
        
        # Логируем завершение генерации
        logging.debug("UI обработал сигнал о завершении генерации")
    
    def show_hide(self):
        """Показать/скрыть окно приложения"""
        if self.isVisible():
            # Если окно видно, скрываем его
            self.hide()
        else:
            # Если окно скрыто, показываем его
            self.show()
            self.activateWindow()
            self.raise_()
            # Устанавливаем фокус на поле ввода
            self.query_input.setFocus()
    
    def center_on_screen(self):
        """Центрирование окна на экране"""
        frame_geometry = self.frameGeometry()
        screen = self.screen().availableGeometry().center()
        frame_geometry.moveCenter(screen)
        self.move(frame_geometry.topLeft())
    
    def closeEvent(self, event):
        """Обработка события закрытия окна"""
        # Сохраняем положение и размер окна
        self.app.settings.setValue("mainwindow/geometry", self.saveGeometry())
        # Скрываем окно вместо закрытия
        self.hide()
        event.ignore() 