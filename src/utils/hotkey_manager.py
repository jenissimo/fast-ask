#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Менеджер глобальных хоткеев с оптимизацией производительности
"""

import os
import logging
import threading
import keyboard

class HotkeyManager:
    """Класс для регистрации и управления глобальными хоткеями"""
    
    def __init__(self):
        """Инициализация менеджера хоткеев"""
        self.registered_hotkeys = {}
        self.running = True
        
        # Создаем список для хранения зарегистрированных хоткеев
        self.hotkeys_list = []
        
        # Флаг для отладки - если включен, хоткеи не регистрируются системно
        self.debug_mode = os.getenv("DEBUG_HOTKEYS", "0").lower() in ("1", "true", "yes")
        
        if not self.debug_mode:
            # Запускаем мониторинг в отдельном потоке с пониженным приоритетом
            self.monitor_thread = threading.Thread(target=self._monitor_hotkeys, daemon=True)
            self.monitor_thread.start()
            
            logging.info("Менеджер хоткеев инициализирован")
        else:
            logging.info("Менеджер хоткеев запущен в режиме отладки (хоткеи отключены)")
    
    def register_hotkey(self, hotkey, callback):
        """Регистрация хоткея и привязка его к функции обратного вызова
        
        Args:
            hotkey (str): Комбинация клавиш (например, 'ctrl+shift+space')
            callback (callable): Функция, которая будет вызвана при нажатии хоткея
        """
        # В режиме отладки просто сохраняем хоткей без системной регистрации
        if self.debug_mode:
            self.registered_hotkeys[hotkey] = callback
            self.hotkeys_list.append(hotkey)
            logging.info(f"Хоткей сохранен (без системной регистрации): {hotkey}")
            return True
            
        # Регистрируем обработчик для данного хоткея
        try:
            keyboard.add_hotkey(hotkey, callback, suppress=False)
            self.registered_hotkeys[hotkey] = callback
            self.hotkeys_list.append(hotkey)
            logging.info(f"Зарегистрирован хоткей: {hotkey}")
            return True
        except Exception as e:
            logging.error(f"Ошибка при регистрации хоткея {hotkey}: {str(e)}")
            return False
    
    def unregister_hotkey(self, hotkey):
        """Удаление зарегистрированного хоткея
        
        Args:
            hotkey (str): Комбинация клавиш для удаления
        """
        if self.debug_mode:
            if hotkey in self.registered_hotkeys:
                self.hotkeys_list.remove(hotkey)
                del self.registered_hotkeys[hotkey]
                logging.info(f"Хоткей удален из списка: {hotkey}")
            return True
            
        if hotkey in self.registered_hotkeys:
            try:
                keyboard.remove_hotkey(hotkey)
                self.hotkeys_list.remove(hotkey)
                del self.registered_hotkeys[hotkey]
                logging.info(f"Удален хоткей: {hotkey}")
                return True
            except Exception as e:
                logging.error(f"Ошибка при удалении хоткея {hotkey}: {str(e)}")
                return False
        return False
    
    def _monitor_hotkeys(self):
        """Фоновый мониторинг хоткеев с низким потреблением ресурсов"""
        # Снижаем приоритет потока для уменьшения нагрузки на систему
        try:
            import time
            # Устанавливаем большой интервал сна для снижения CPU нагрузки
            while self.running:
                time.sleep(0.5)  # Увеличенный интервал для снижения нагрузки
        except Exception as e:
            logging.error(f"Ошибка в мониторинге хоткеев: {str(e)}")
    
    def get_registered_hotkeys(self):
        """Получение списка зарегистрированных хоткеев"""
        return self.hotkeys_list
    
    def stop(self):
        """Остановка работы менеджера хоткеев и освобождение ресурсов"""
        if self.debug_mode:
            logging.info("Остановка менеджера хоткеев (режим отладки)")
            return
            
        self.running = False
        
        # Удаляем все зарегистрированные хоткеи
        for hotkey in list(self.registered_hotkeys.keys()):
            self.unregister_hotkey(hotkey)
        
        logging.info("Менеджер хоткеев остановлен") 