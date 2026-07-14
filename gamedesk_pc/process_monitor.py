"""
Модуль мониторинга процессов через psutil.

Отвечает за определение активной игровой сессии по списку известных процессов.
"""

import psutil
from config import GAMES


class ProcessMonitor:
    """Мониторинг запущенных игровых процессов."""

    @staticmethod
    def _get_process_name_list() -> list:
        """
        Возвращает список имён процессов (в нижнем регистре) из словаря GAMES.

        Используется для быстрого сравнения без учёта регистра.
        """
        return [name.lower() for name in GAMES.keys()]

    @staticmethod
    def get_active_game() -> str | None:
        """
        Проверяет запущенные процессы и возвращает отображаемое название первой найденной игры.

        Алгоритм:
        1. Перебирает все запущенные процессы через psutil.process_iter(['name']).
        2. Приводит имя процесса к нижнему регистру и ищет в списке известных имён.
        3. При совпадении возвращает соответствующее отображаемое имя из GAMES.
        4. Если ничего не найдено — возвращает None.

        Регистр имён игнорируется, расширение .exe не обязательно (но обычно присутствует).
        Если запущено несколько игр, возвращается первая обнаруженная.
        """
        # Получаем список эталонных имён (нижний регистр) для быстрого поиска
        known_names_lower = ProcessMonitor._get_process_name_list()

        # Перебираем все запущенные процессы
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name']
                if proc_name is None:
                    continue
                proc_name_lower = proc_name.lower()
                # Проверяем, есть ли такое имя в списке известных
                if proc_name_lower in known_names_lower:
                    # Находим оригинальный ключ (с учётом регистра) для получения отображаемого имени
                    for full_name, display_name in GAMES.items():
                        if full_name.lower() == proc_name_lower:
                            return display_name
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Игнорируем процессы, которые завершились или недоступны
                continue
        return None

    @staticmethod
    def get_running_processes() -> list:
        """
        Возвращает список имён всех запущенных процессов (для отладки).

        Полезна для проверки, какие процессы видны системе.
        """
        process_names = []
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name']
                if name:
                    process_names.append(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return process_names