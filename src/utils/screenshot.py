#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Модуль для работы со скриншотами
"""

import os
import base64
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageGrab
from PyQt6.QtWidgets import QRubberBand, QWidget, QApplication
from PyQt6.QtCore import QRect, QPoint, Qt, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor, QScreen, QGuiApplication

class ScreenshotSelection(QWidget):
    """Виджет для выбора области экрана"""
    
    def __init__(self):
        """Инициализация виджета выбора области экрана"""
        super().__init__()
        
        # Флаг выбора области
        self.selection_active = False
        
        # Начальная и конечная точки выбора
        self.origin = QPoint()
        self.current = QPoint()
        
        # Резиновая область для визуализации выбора
        self.rubberband = QRubberBand(QRubberBand.Shape.Rectangle, self)
        
        # Настройка внешнего вида
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Показываем окно
        self.showFullScreen()
    
    def paintEvent(self, event):
        """Отрисовка полупрозрачного наложения на экран"""
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Полупрозрачное затемнение всего экрана
        overlay_color = QColor(0, 0, 0, 128)  # RGBA: полупрозрачный черный
        painter.setBrush(overlay_color)
        painter.drawRect(0, 0, self.width(), self.height())
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key.Key_Escape:
            # Отмена выбора по Escape
            self.close()
    
    def mousePressEvent(self, event):
        """Обработка нажатия кнопки мыши"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.selection_active = True
            self.origin = event.pos()
            self.rubberband.setGeometry(QRect(self.origin, QSize(0, 0)))
            self.rubberband.show()
    
    def mouseMoveEvent(self, event):
        """Обработка движения мыши"""
        if self.selection_active:
            self.current = event.pos()
            self.rubberband.setGeometry(QRect(self.origin, self.current).normalized())
    
    def mouseReleaseEvent(self, event):
        """Обработка отпускания кнопки мыши"""
        if event.button() == Qt.MouseButton.LeftButton and self.selection_active:
            self.current = event.pos()
            self.selection_active = False
            self.rubberband.hide()
            self.close()

class ScreenshotManager(QObject):
    """Менеджер для работы со скриншотами"""
    
    # Сигнал о захвате скриншота
    screenshot_captured = pyqtSignal(object)
    
    def __init__(self, screenshots_dir=None):
        """Инициализация менеджера скриншотов"""
        super().__init__()
        
        # Директория для сохранения скриншотов
        if screenshots_dir:
            self.screenshots_dir = Path(screenshots_dir)
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.screenshots_dir = Path(tempfile.gettempdir()) / "fastask_screenshots"
            self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Текущее изображение
        self.current_image = None
        
        # Виджет выбора области
        self.selection_widget = None
        
        logging.info(f"Менеджер скриншотов инициализирован. Папка: {self.screenshots_dir}")
    
    def capture(self):
        """Запуск процесса выбора области и захвата скриншота"""
        # Создаем виджет выбора области
        self.selection_widget = ScreenshotSelection()
        
        # Подключаем обработчик закрытия виджета
        self.selection_widget.destroyed.connect(self._on_selection_closed)
    
    def _on_selection_closed(self):
        """Обработка закрытия виджета выбора области"""
        if not self.selection_widget:
            return
        
        # Получаем геометрию выбранной области
        selection_rect = self.selection_widget.rubberband.geometry()
        
        # Если пользователь отменил выбор или ничего не выбрал
        if selection_rect.width() <= 5 or selection_rect.height() <= 5:
            logging.info("Выбор области скриншота отменен")
            self.screenshot_captured.emit(None)
            return
        
        # Получаем позицию области относительно экрана
        global_pos = self.selection_widget.mapToGlobal(selection_rect.topLeft())
        
        # Делаем скриншот выбранной области
        screen = QGuiApplication.primaryScreen()
        screenshot = screen.grabWindow(
            0,  # Захват всего экрана
            global_pos.x(),
            global_pos.y(),
            selection_rect.width(),
            selection_rect.height()
        )
        
        # Сохраняем скриншот во временный файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self.screenshots_dir / f"screenshot_{timestamp}.png"
        
        saved = screenshot.save(str(screenshot_path), "PNG")
        if saved:
            logging.info(f"Скриншот сохранен: {screenshot_path}")
            # Эмитим сигнал с путем к файлу скриншота
            self.screenshot_captured.emit(screenshot_path)
        else:
            logging.error("Ошибка сохранения скриншота")
            self.screenshot_captured.emit(None)
    
    @staticmethod
    def get_base64_image(image_path):
        """Преобразование изображения в base64 для отправки в API
        
        Args:
            image_path (str or Path): Путь к файлу изображения
            
        Returns:
            str: Строка в формате base64
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logging.error(f"Ошибка при кодировании изображения в base64: {str(e)}")
            return None 