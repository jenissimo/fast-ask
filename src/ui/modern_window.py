#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Современное главное окно приложения FastAsk с минималистичным дизайном
"""

import os
import logging
import markdown
from enum import Enum
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QColor, QKeySequence, QShortcut, QFontMetrics, QClipboard

class Mode(Enum):
    """Режимы работы окна"""
    HISTORY = 0
    INPUT = 1
    ANSWER = 2

class ModernWindow(QMainWindow):
    """Современное главное окно приложения FastAsk"""
    
    # Сигнал для отправки запроса к API
    send_request = pyqtSignal(str, object)
    
    # Сигнал для прерывания генерации
    stop_generation = pyqtSignal()
    
    def __init__(self, app):
        """Инициализация главного окна приложения"""
        super().__init__()
        
        self.app = app
        self.screenshot = None
        
        # Текущий режим отображения
        self.current_mode = Mode.HISTORY
        
        # Настраиваем окно
        self._setup_window()
        
        # Инициализируем UI компоненты
        self._init_ui()
        
        # Подключаем сигналы
        self._connect_signals()
        
        # Состояние генерации ответа
        self.is_generating = False
        
        # Загружаем историю запросов
        self._load_history()
        
        logging.info("Современное главное окно инициализировано")
    
    def _setup_window(self):
        """Настройка параметров окна"""
        # Настройки внешнего вида
        self.setWindowTitle("FastAsk")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(600, 400)
        
        # Устанавливаем начальный размер окна перед центрированием
        self.resize(700, 500)
        
        # Загружаем настройки позиции и размера
        geometry = self.app.settings.value("mainwindow/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # По умолчанию центрируем на экране
            self.center_on_screen()
    
    def _init_ui(self):
        """Инициализация интерфейса"""
        # Центральный виджет
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Добавляем эффект тени
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 0)
        self.central_widget.setGraphicsEffect(shadow)
        
        # Основной лейаут
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)
        
        # Создаем и стилизуем фрейм для красивого фона
        self.bg_frame = QFrame(self.central_widget)
        self.bg_frame.setObjectName("bgFrame")
        self.bg_frame.setStyleSheet("""
            QFrame#bgFrame {
                background-color: rgba(30, 30, 35, 220);
                border-radius: 15px;
            }
        """)
        self.bg_layout = QVBoxLayout(self.bg_frame)
        self.bg_layout.setContentsMargins(20, 20, 20, 20)
        self.bg_layout.setSpacing(15)
        
        # Вставляем фрейм в основной лейаут
        self.main_layout.addWidget(self.bg_frame)
        
        # Поле ввода запроса с авторесайзом
        self.query_input = QTextEdit()
        self.query_input.setPlaceholderText("Задайте вопрос или нажмите ? для списка команд...")
        self.query_input.setAcceptRichText(False)
        self.query_input.setStyleSheet("""
            QTextEdit {
                background-color: rgba(45, 45, 50, 150);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        # Установка минимальной высоты для одной строки и максимальной для 4 строк
        line_height = QFontMetrics(self.query_input.font()).lineSpacing()
        self.query_input.setMinimumHeight(line_height + 30)  # +30 для учета внутренних отступов
        self.query_input.setMaximumHeight(line_height * 4 + 30)  # Максимум 4 строки, потом скролл
        self.bg_layout.addWidget(self.query_input)
        
        # Лейаут для поля ответа и кнопки копирования
        self.response_layout = QVBoxLayout()
        
        # Поле для вывода ответа (изначально скрыто)
        self.response_output = QTextEdit()
        self.response_output.setReadOnly(True)
        self.response_output.setVisible(False)
        self.response_output.setStyleSheet("""
            QTextEdit {
                background-color: rgba(45, 45, 50, 120);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        
        # Контейнер для поля ответа и кнопки копирования
        self.response_container = QWidget()
        self.response_container.setVisible(False)
        self.response_container_layout = QHBoxLayout(self.response_container)
        self.response_container_layout.setContentsMargins(0, 0, 0, 0)
        self.response_container_layout.setSpacing(10)
        
        # Добавляем поле ответа в контейнер
        self.response_container_layout.addWidget(self.response_output, 1)
        
        # Создаем вертикальный лейаут для кнопки копирования
        self.copy_button_layout = QVBoxLayout()
        self.copy_button_layout.setContentsMargins(0, 0, 0, 0)
        self.copy_button_layout.setSpacing(0)
        
        # Кнопка копирования
        self.copy_button = QPushButton("📋")
        self.copy_button.setToolTip("Копировать ответ в буфер обмена")
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(60, 60, 65, 150);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 85, 200);
            }
        """)
        self.copy_button.clicked.connect(self._copy_response)
        
        # Добавляем кнопку копирования в вертикальный лейаут с растяжкой сверху
        self.copy_button_layout.addStretch(1)
        self.copy_button_layout.addWidget(self.copy_button)
        self.copy_button_layout.addStretch(1)
        
        # Добавляем вертикальный лейаут в контейнер
        self.response_container_layout.addLayout(self.copy_button_layout)
        
        # Добавляем контейнер в основной лейаут
        self.bg_layout.addWidget(self.response_container)
        
        # Список истории (изначально видим)
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                margin: 2px 0px;
                border-radius: 5px;
            }
            QListWidget::item:hover {
                background-color: rgba(60, 60, 65, 150);
            }
            QListWidget::item:selected {
                background-color: rgba(70, 130, 180, 150);
            }
        """)
        self.bg_layout.addWidget(self.history_list)
        
        # Индикатор состояния и подсказки
        self.status_layout = QHBoxLayout()
        
        # Информация о скриншоте и статус
        self.status_label = QLabel("Ctrl+Shift+S для скриншота")
        self.status_label.setStyleSheet("color: rgba(200, 200, 200, 150); font-size: 11px;")
        self.status_layout.addWidget(self.status_label)
        
        # Распорка
        self.status_layout.addStretch(1)
        
        # Кнопка для отмены/остановки
        self.cancel_button = QPushButton("✕")
        self.cancel_button.setToolTip("Закрыть окно (Esc)")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(180, 40, 40, 150);
                color: white;
                border: none;
                border-radius: 15px;
                padding: 5px;
                font-size: 12px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background-color: rgba(220, 40, 40, 200);
            }
        """)
        self.cancel_button.clicked.connect(self.hide)
        
        # Кнопка стоп (только при генерации)
        self.stop_button = QPushButton("⏹")
        self.stop_button.setToolTip("Остановить генерацию (Esc)")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(40, 120, 180, 150);
                color: white;
                border: none;
                border-radius: 15px;
                padding: 5px;
                font-size: 12px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background-color: rgba(40, 150, 220, 200);
            }
        """)
        self.stop_button.clicked.connect(self._stop_generation)
        self.stop_button.setVisible(False)
        
        # Добавляем кнопки 
        self.status_layout.addWidget(self.stop_button)
        self.status_layout.addWidget(self.cancel_button)
        
        # Добавляем статусный лейаут в основной
        self.bg_layout.addLayout(self.status_layout)
    
    def _connect_signals(self):
        """Подключение обработчиков сигналов"""
        # Горячие клавиши
        self.esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.esc_shortcut.activated.connect(self._handle_escape)
        
        # Отправка запроса по Enter (если не зажат Shift или Ctrl)
        self.query_input.installEventFilter(self)
        
        # Отслеживаем изменения в поле ввода
        self.query_input.textChanged.connect(self._on_input_changed)
        
        # Клик по элементу истории
        self.history_list.itemClicked.connect(self._on_history_item_clicked)
    
    def eventFilter(self, obj, event):
        """Обработка событий для перехвата нажатия Enter"""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QKeyEvent
        
        if obj is self.query_input and event.type() == QEvent.Type.KeyPress:
            # Правильно получаем событие клавиатуры - оно уже является QKeyEvent
            if isinstance(event, QKeyEvent):
                
                # Обрабатываем Enter для отправки запроса (без Shift или Ctrl)
                if (event.key() == Qt.Key.Key_Return or 
                    event.key() == Qt.Key.Key_Enter):
                    
                    # Если зажаты Shift или Ctrl, просто пропускаем для обычного переноса строки
                    if not (event.modifiers() & (Qt.KeyboardModifier.ShiftModifier | 
                                                Qt.KeyboardModifier.ControlModifier)):
                        self._on_send_clicked()
                        return True
        
        return super().eventFilter(obj, event)
    
    def _handle_escape(self):
        """Обработка нажатия Escape"""
        if self.is_generating:
            # Если идет генерация, останавливаем её
            self._stop_generation()
        else:
            # Иначе скрываем окно
            self.hide()
    
    def _on_input_changed(self):
        """Обработка изменения текста в поле ввода"""
        text = self.query_input.toPlainText().strip()
        
        if not text and self.current_mode != Mode.HISTORY:
            # Если поле пустое, переключаемся в режим истории
            self._switch_mode(Mode.HISTORY)
        elif text and self.current_mode == Mode.HISTORY:
            # Если ввели текст, переключаемся в режим ввода
            self._switch_mode(Mode.INPUT)
    
    def _switch_mode(self, new_mode):
        """Переключение между режимами отображения
        
        Args:
            new_mode (Mode): Новый режим отображения
        """
        self.current_mode = new_mode
        
        # Анимация смены режима
        if new_mode == Mode.HISTORY:
            # Показываем историю, скрываем поле ответа
            self.history_list.setVisible(True)
            self.response_container.setVisible(False)
            self.query_input.setPlaceholderText("Задайте вопрос или нажмите ? для списка команд...")
            
            # Фокус на поле ввода
            self.query_input.clear()
            self.query_input.setFocus()
            
            # Сбрасываем скриншот
            self.screenshot = None
            
            # Обновляем подсказку
            self.status_label.setText("Ctrl+Shift+S для скриншота")
            
        elif new_mode == Mode.ANSWER:
            # Показываем ответ, скрываем историю
            self.history_list.setVisible(False)
            self.response_container.setVisible(True)
            self.response_output.setVisible(True)
            
            # Плейсхолдер для поля ввода
            self.query_input.setPlaceholderText("Задайте новый вопрос или введите ? для справки...")
            
            # Обновляем подсказку со скриншотом
            if self.screenshot:
                self.status_label.setText("Используется скриншот для контекста")
            else:
                self.status_label.setText("Введите новый запрос для продолжения")
            
        self.repaint()  # Принудительное обновление для немедленного отображения изменений
    
    def _on_send_clicked(self):
        """Обработка нажатия кнопки отправки запроса"""
        # Получаем текст запроса
        query = self.query_input.toPlainText().strip()
        
        # Если запрос пустой, ничего не делаем
        if not query:
            return
        
        # Если уже идет генерация, ничего не делаем
        if self.is_generating:
            return
        
        # Устанавливаем флаг генерации
        self.is_generating = True
        
        # Сбрасываем текущий ответ
        if hasattr(self, 'current_response'):
            delattr(self, 'current_response')
        
        # Очищаем поле ответа
        self.response_output.clear()
        
        # Переключаемся в режим ответа
        self._switch_mode(Mode.ANSWER)
        
        # Показываем кнопку остановки и обновляем статус
        self.stop_button.setVisible(True)
        self.status_label.setText("Генерация ответа...")
        
        # Отправляем запрос
        self.send_request.emit(query, self.screenshot)
    
    def _stop_generation(self):
        """Прерывание генерации ответа"""
        if self.is_generating:
            # Сохраняем текущее накопленное значение как финальный ответ
            if hasattr(self, 'current_response'):
                # Генерируем сообщение о прерывании
                self.current_response += "\n\n*Генерация прервана пользователем*"
                # Преобразуем в HTML
                html_content = markdown.markdown(self.current_response)
                self.response_output.setHtml(html_content)
            
            # Отправляем сигнал остановки
            self.stop_generation.emit()
            
            # Обновляем состояние интерфейса
            self._reset_generation_state()
            
            # Обновляем статус
            self.status_label.setText("Генерация остановлена")
    
    def _reset_generation_state(self):
        """Сброс состояния генерации ответа"""
        self.is_generating = False
        self.stop_button.setVisible(False)
        
        # Обновляем историю
        self._load_history()
        
        # Обновляем статус
        self.status_label.setText("Готово • Ctrl+Shift+S для нового запроса со скриншотом")
    
    def on_screenshot_captured(self, screenshot):
        """Обработка захваченного скриншота"""
        # Показываем окно после захвата и центрируем его
        self.center_on_screen()
        self.show()
        self.activateWindow()
        self.raise_()
        
        if screenshot is not None:
            self.screenshot = screenshot
            self.status_label.setText("Скриншот прикреплен • Enter для отправки")
    
    def on_response_received(self, response):
        """Обработка получения полного ответа (не потоковый)"""
        self.on_generation_complete(response)
    
    def on_response_chunk(self, chunk):
        """Обработка получения части ответа при потоковой генерации"""
        # Добавляем полученный текст в поле ответа
        current_text = self.response_output.toHtml()
        
        # Если это первый чанк, очищаем поле
        if not hasattr(self, 'current_response'):
            self.current_response = ""
            self.response_output.clear()
            current_text = ""
        
        # Добавляем текст к накопленному ответу
        self.current_response += chunk
        
        # Преобразуем Markdown в HTML
        html_content = markdown.markdown(self.current_response)
        self.response_output.setHtml(html_content)
        
        # Переключаемся в режим ответа, если еще не переключились
        if self.current_mode != Mode.ANSWER:
            self._switch_mode(Mode.ANSWER)
            
            # Показываем кнопку остановки
            self.stop_button.setVisible(True)
            self.status_label.setText("Генерация ответа...")
    
    def on_generation_complete(self, full_response):
        """Обработка завершения генерации ответа"""
        # Если генерация остановлена пользователем, не обновляем ответ
        if not self.is_generating:
            return
            
        # Сохраняем полный ответ
        self.current_response = full_response
        
        # Преобразуем Markdown в HTML
        html_content = markdown.markdown(full_response)
        self.response_output.setHtml(html_content)
        
        # Скрываем кнопку остановки
        self.stop_button.setVisible(False)
        
        # Обновляем статусную строку
        if self.screenshot:
            self.status_label.setText("Ответ сгенерирован с использованием скриншота")
        else:
            self.status_label.setText("Ответ сгенерирован")
        
        # Генерация завершена
        self.is_generating = False
        
        # Обновляем историю запросов
        self._load_history()
    
    def _load_history(self):
        """Загрузка истории запросов"""
        # Очищаем список
        self.history_list.clear()
        
        # Получаем историю из базы данных (10 последних запросов)
        if hasattr(self.app, 'db_manager'):
            history_items = self.app.db_manager.get_history(limit=10, offset=0)
            
            # Если есть история, добавляем элементы в список
            if history_items:
                for item in reversed(history_items):  # Показываем новые сверху
                    # Создаем элемент списка
                    list_item = QListWidgetItem(item['query'][:60] + ('...' if len(item['query']) > 60 else ''))
                    list_item.setToolTip(item['query'])
                    
                    # Сохраняем полные данные в элемент
                    list_item.setData(Qt.ItemDataRole.UserRole, item)
                    
                    # Добавляем элемент в список
                    self.history_list.addItem(list_item)
    
    def _on_history_item_clicked(self, item):
        """Обработка клика по элементу истории"""
        # Получаем данные элемента
        history_item = item.data(Qt.ItemDataRole.UserRole)
        
        if history_item:
            # Заполняем поле ввода текстом запроса
            self.query_input.setPlainText(history_item['query'])
            
            # Устанавливаем ответ
            self.response_output.setPlainText(history_item['response'])
            
            # Переключаемся в режим ответа
            self._switch_mode(Mode.ANSWER)
            
            # Сбрасываем состояние генерации (ответ уже готов)
            self.is_generating = False
            self.stop_button.setVisible(False)
            
            # Обновляем статус
            self.status_label.setText("Из истории • Ctrl+Shift+S для нового запроса со скриншотом")
    
    def show_hide(self):
        """Показать/скрыть окно приложения"""
        if self.isVisible():
            # Если окно видно, скрываем его
            self.hide()
        else:
            # Если окно скрыто, показываем его и центрируем
            self.center_on_screen()
            self.show()
            self.activateWindow()
            self.raise_()
            # Устанавливаем фокус на поле ввода
            self.query_input.setFocus()
    
    def center_on_screen(self):
        """Центрирование окна на экране"""
        # Получаем доступный размер экрана (с учетом панели задач)
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        
        # Создаем геометрию окна для центрирования
        frame_geometry = self.frameGeometry()
        # Устанавливаем центр геометрии окна в центр экрана
        frame_geometry.moveCenter(screen_geometry.center())
        # Перемещаем окно в новую позицию
        self.move(frame_geometry.topLeft())
    
    def closeEvent(self, event):
        """Обработка события закрытия окна"""
        # Сохраняем положение и размер окна
        self.app.settings.setValue("mainwindow/geometry", self.saveGeometry())
        # Скрываем окно вместо закрытия
        self.hide()
        event.ignore()
    
    def mousePressEvent(self, event):
        """Обработка нажатия кнопки мыши"""
        # Запоминаем позицию для перетаскивания окна
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
    
    def mouseMoveEvent(self, event):
        """Обработка движения мыши"""
        # Перетаскивание окна
        if hasattr(self, '_drag_pos') and event.buttons() & Qt.MouseButton.LeftButton:
            diff = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + diff)
            self._drag_pos = event.globalPosition().toPoint()
    
    def _copy_response(self):
        """Копирует текст ответа в буфер обмена"""
        if hasattr(self, 'current_response'):
            clipboard = QApplication.clipboard()
            clipboard.setText(self.current_response)
            
            # Показываем временное сообщение о копировании
            previous_text = self.status_label.text()
            self.status_label.setText("Ответ скопирован в буфер обмена")
            self.status_label.setStyleSheet("color: rgba(100, 220, 100, 200); font-size: 11px;")
            
            # Через 2 секунды возвращаем предыдущий текст
            QTimer.singleShot(2000, lambda: self._reset_status_label(previous_text))
    
    def _reset_status_label(self, text):
        """Возвращает статусному сообщению предыдущий текст и стиль"""
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: rgba(200, 200, 200, 150); font-size: 11px;")