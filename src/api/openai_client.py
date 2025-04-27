#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Клиент для работы с OpenAI API (использует официальный SDK)
"""

import os
import json
import logging
import threading
from typing import Optional, Dict, Any, List, Callable, Generator
from openai import OpenAI, AsyncOpenAI


class OpenAIClient:
    """Клиент для работы с OpenAI API с поддержкой прерывания генерации"""
    
    def __init__(self, api_key=None, api_url=None, model=None):
        """Инициализация клиента OpenAI
        
        Args:
            api_key (str, optional): API ключ OpenAI или OpenRouter
            api_url (str, optional): URL API сервера
            model (str, optional): Название модели
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.api_url = api_url or os.getenv("OPENAI_API_URL", "https://api.openai.com")
        self.model = model or os.getenv("OPENAI_MODEL", "google/gemini-2.5-flash")
        
        # Флаг для прерывания генерации
        self.cancel_generation = threading.Event()
        
        # Определяем дополнительные HTTP-заголовки для OpenRouter
        extra_headers = {}
        if "openrouter.ai" in self.api_url:
            extra_headers = {
                "HTTP-Referer": "https://github.com/user/fast-ask",  # URL проекта
                "X-Title": "FastAsk"  # Название приложения
            }
        
        # Инициализация клиентов
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
            default_headers=extra_headers
        )
        
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
            default_headers=extra_headers
        )
        
        # Проверяем наличие API ключа
        if not self.api_key:
            logging.error("API ключ не найден. Задайте его в .env файле или при инициализации.")
        
        logging.info(f"API клиент инициализирован. Модель: {self.model}, URL: {self.api_url}")
    
    def create_chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        on_chunk: Optional[Callable[[str], None]] = None,
        on_finish: Optional[Callable[[], None]] = None
    ) -> str:
        """Синхронный запрос к chat/completions API
        
        Args:
            messages: Список сообщений в формате OpenAI
            temperature: Температура генерации (0.0 - 1.0)
            max_tokens: Максимальное количество токенов в ответе
            stream: Использовать потоковую генерацию
            on_chunk: Коллбэк для обработки частей ответа при потоковой генерации
            on_finish: Коллбэк, вызываемый при завершении генерации
            
        Returns:
            str: Сгенерированный ответ
        """
        # Сбрасываем флаг отмены
        self.cancel_generation.clear()
        
        try:
            if stream:
                full_response = ""
                
                # Потоковая генерация
                response_stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                
                # Обрабатываем поток ответов
                for chunk in response_stream:
                    # Проверяем, не была ли отменена генерация
                    if self.cancel_generation.is_set():
                        logging.info("Генерация ответа была прервана пользователем")
                        response_stream.close()
                        break
                    
                    # Проверяем, есть ли признак завершения
                    if hasattr(chunk.choices[0], "finish_reason") and chunk.choices[0].finish_reason is not None:
                        logging.info(f"Генерация завершена, причина: {chunk.choices[0].finish_reason}")
                        # Вызываем колбэк завершения
                        if on_finish:
                            on_finish()
                        break
                    
                    # Извлекаем текст из чанка если он есть
                    if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        
                        # Вызываем коллбэк с текстом чанка
                        if on_chunk:
                            on_chunk(content)
                
                # Если мы вышли из цикла без явного вызова on_finish, вызываем его сейчас
                if on_finish and not self.cancel_generation.is_set():
                    on_finish()
                
                return full_response
            else:
                # Обычная генерация
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                return response.choices[0].message.content
                
        except Exception as e:
            error_message = f"Ошибка: Не удалось получить ответ от OpenAI API. {str(e)}"
            logging.error(error_message)
            
            if on_chunk and stream:
                on_chunk(error_message)
                
            return error_message
    
    async def create_chat_completion_async(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        on_chunk: Optional[Callable[[str], None]] = None,
        on_finish: Optional[Callable[[], None]] = None
    ) -> str:
        """Асинхронный запрос к chat/completions API
        
        Args:
            messages: Список сообщений в формате OpenAI
            temperature: Температура генерации (0.0 - 1.0)
            max_tokens: Максимальное количество токенов в ответе
            stream: Использовать потоковую генерацию
            on_chunk: Коллбэк для обработки частей ответа
            on_finish: Коллбэк, вызываемый при завершении генерации
            
        Returns:
            str: Сгенерированный ответ
        """
        # Сбрасываем флаг отмены
        self.cancel_generation.clear()
        
        try:
            if stream:
                full_response = ""
                
                # Потоковая генерация
                response_stream = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                
                # Обрабатываем поток ответов
                async for chunk in response_stream:
                    # Проверяем, не была ли отменена генерация
                    if self.cancel_generation.is_set():
                        logging.info("Генерация ответа была прервана пользователем")
                        await response_stream.aclose()
                        break
                    
                    # Извлекаем текст из чанка если он есть
                    if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        
                        # Вызываем коллбэк с текстом чанка
                        if on_chunk:
                            on_chunk(content)

                    # Проверяем, есть ли признак завершения
                    if hasattr(chunk.choices[0], "finish_reason") and chunk.choices[0].finish_reason is not None:
                        logging.info(f"Генерация завершена, причина: {chunk.choices[0].finish_reason}")
                        # Вызываем колбэк завершения
                        if on_finish:
                            on_finish()
                        break
                
                # Если мы вышли из цикла без явного вызова on_finish, вызываем его сейчас
                if on_finish and not self.cancel_generation.is_set():
                    on_finish()
                    
                return full_response
            else:
                # Обычная генерация
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                return response.choices[0].message.content
                
        except Exception as e:
            error_message = f"Ошибка: Не удалось получить ответ от OpenAI API. {str(e)}"
            logging.error(error_message)
            
            if on_chunk and stream:
                on_chunk(error_message)
                
            return error_message
    
    def cancel(self):
        """Отмена текущей генерации ответа"""
        self.cancel_generation.set()
        logging.info("Запрошена отмена генерации ответа")
    
    def create_system_message(self, content: str) -> Dict[str, str]:
        """Создание системного сообщения"""
        return {"role": "system", "content": content}
    
    def create_user_message(self, content: str) -> Dict[str, str]:
        """Создание пользовательского сообщения"""
        return {"role": "user", "content": content}
    
    def create_assistant_message(self, content: str) -> Dict[str, str]:
        """Создание сообщения ассистента"""
        return {"role": "assistant", "content": content}
    
    def create_image_message(self, text_content: str, image_path: str) -> List[Dict[str, Any]]:
        """Создание сообщения с изображением для vision-модели
        
        Args:
            text_content (str): Текстовая часть сообщения
            image_path (str): Путь к изображению
            
        Returns:
            List[Dict[str, Any]]: Сообщение в формате для vision-модели
        """
        from src.utils.screenshot import ScreenshotManager
        
        # Получаем base64 для изображения
        image_base64 = ScreenshotManager.get_base64_image(image_path)
        if not image_base64:
            return [{"type": "text", "text": text_content}]
        
        # Формируем сообщение с изображением
        return [
            {"type": "text", "text": text_content},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}"
                }
            }
        ]

    async def _stream_chat_completion_async(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7, 
        max_tokens: int = 1000,
        on_chunk: Optional[Callable[[str], None]] = None
    ) -> str:
        """Асинхронная потоковая генерация ответа
        
        Args:
            messages: Список сообщений в формате OpenAI
            temperature: Температура генерации (0.0 - 1.0)
            max_tokens: Максимальное количество токенов в ответе
            on_chunk: Коллбэк для обработки частей ответа
            
        Returns:
            str: Сгенерированный ответ целиком
        """
        # Формируем URL
        url = f"{self.api_url}/chat/completions"
        
        # Формируем данные запроса
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        
        full_response = "" 