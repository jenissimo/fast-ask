#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Менеджер базы данных для хранения истории запросов
"""

import sqlite3
import logging
import json
from datetime import datetime
from pathlib import Path

class DatabaseManager:
    """Класс для работы с базой данных SQLite"""
    
    def __init__(self, db_path="data/history.db"):
        """Инициализация соединения с базой данных"""
        self.db_path = db_path
        
        # Создаем директорию для БД, если её нет
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Инициализация базы данных
        self._initialize_db()
    
    def _initialize_db(self):
        """Инициализация схемы базы данных"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Создаем таблицу для истории запросов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            response TEXT NOT NULL,
            has_screenshot INTEGER DEFAULT 0,
            screenshot_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            model_name TEXT,
            metadata TEXT
        )
        ''')
        
        # Создаем индекс для ускорения поиска
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        
        logging.info(f"База данных инициализирована: {self.db_path}")
    
    def _get_connection(self):
        """Получение соединения с базой данных"""
        return sqlite3.connect(self.db_path)
    
    def add_history_item(self, query, response, has_screenshot=False, 
                         screenshot_path=None, model_name=None, metadata=None):
        """Добавление записи в историю запросов"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Преобразуем metadata в JSON, если есть
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
        INSERT INTO history (
            query, response, has_screenshot, screenshot_path, 
            timestamp, model_name, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            query, response, 1 if has_screenshot else 0,
            screenshot_path, datetime.now().isoformat(),
            model_name, metadata_json
        ))
        
        history_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logging.debug(f"Добавлен новый запрос в историю, ID: {history_id}")
        return history_id
    
    def get_history(self, limit=50, offset=0, query_filter=None):
        """Получение истории запросов с пагинацией и фильтрацией"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        sql = "SELECT * FROM history"
        params = []
        
        # Добавляем фильтр если есть
        if query_filter:
            sql += " WHERE query LIKE ? OR response LIKE ?"
            params.extend([f"%{query_filter}%", f"%{query_filter}%"])
        
        # Сортировка и пагинация
        sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(sql, params)
        history_items = cursor.fetchall()
        
        # Получение информации о колонках
        columns = [description[0] for description in cursor.description]
        
        conn.close()
        
        # Преобразуем список в словари с ключами-названиями колонок
        result = []
        for item in history_items:
            history_dict = dict(zip(columns, item))
            
            # Преобразуем JSON обратно в словарь
            if history_dict.get("metadata"):
                try:
                    history_dict["metadata"] = json.loads(history_dict["metadata"])
                except json.JSONDecodeError:
                    logging.error(f"Ошибка при декодировании JSON для записи: {history_dict['id']}")
            
            result.append(history_dict)
            
        return result
    
    def get_history_item(self, history_id):
        """Получение конкретной записи из истории по ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM history WHERE id = ?", (history_id,))
        item = cursor.fetchone()
        
        if not item:
            conn.close()
            return None
        
        # Получение информации о колонках
        columns = [description[0] for description in cursor.description]
        
        conn.close()
        
        # Преобразуем в словарь
        history_dict = dict(zip(columns, item))
        
        # Преобразуем JSON обратно в словарь
        if history_dict.get("metadata"):
            try:
                history_dict["metadata"] = json.loads(history_dict["metadata"])
            except json.JSONDecodeError:
                logging.error(f"Ошибка при декодировании JSON для записи: {history_dict['id']}")
        
        return history_dict
    
    def delete_history_item(self, history_id):
        """Удаление записи из истории"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM history WHERE id = ?", (history_id,))
        conn.commit()
        
        deleted = cursor.rowcount > 0
        conn.close()
        
        if deleted:
            logging.debug(f"Удалена запись из истории, ID: {history_id}")
        
        return deleted
    
    def clear_history(self):
        """Очистка всей истории запросов"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM history")
        conn.commit()
        
        deleted_count = cursor.rowcount
        conn.close()
        
        logging.info(f"История очищена. Удалено записей: {deleted_count}")
        return deleted_count 