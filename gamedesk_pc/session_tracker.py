"""
Модуль учёта времени игровых сессий.

Отслеживает начало, окончание и текущую длительность игровой сессии.
Вся логика времени находится на стороне ПК (Python).
"""

import time
from typing import Optional


class SessionTracker:
    """Класс для управления игровой сессией."""

    def __init__(self):
        """Инициализирует трекер: сессия неактивна, время начала не задано."""
        self._game_name: Optional[str] = None
        self._start_time: Optional[float] = None   # время в секундах (time.time())

    def start_session(self, game_name: str) -> None:
        """
        Начинает новую игровую сессию.

        Если сессия уже активна, она будет завершена (перезапущена) с выводом предупреждения.
        В реальном использовании следует сначала вызывать end_session(), но для надёжности
        предусмотрена автоматическая замена.

        Args:
            game_name: отображаемое название игры (из GAMES).
        """
        if self.is_active():
            # Если сессия уже идёт, завершаем её (перезапуск)
            old_game = self._game_name
            duration = self.get_session_duration()
            print(f"[WARNING] Сессия {old_game} уже активна ({self._format_duration(duration)}). Перезапуск.")
            self.end_session()

        self._game_name = game_name
        self._start_time = time.time()
        print(f"[{game_name}] Сессия начата")

    def end_session(self) -> Optional[int]:
        """
        Завершает текущую игровую сессию.

        Возвращает длительность в секундах или None, если сессия не была активна.
        После вызова состояние сбрасывается.

        Returns:
            int: длительность сессии в секундах, или None, если сессия не активна.
        """
        if not self.is_active():
            return None

        duration = self.get_session_duration()
        game_name = self._game_name
        duration_str = self._format_duration(duration)

        # Сбрасываем состояние
        self._game_name = None
        self._start_time = None

        print(f"[{game_name}] Сессия завершена: {duration_str}")
        return duration

    def get_session_duration(self) -> int:
        """
        Возвращает текущую длительность сессии в секундах.

        Если сессия не активна, возвращает 0.
        """
        if not self.is_active():
            return 0
        return int(time.time() - self._start_time)

    def get_session_str(self) -> str:
        """
        Возвращает строковое представление текущей длительности сессии в формате HH:MM:SS.

        Если сессия не активна, возвращает "00:00:00".
        """
        duration = self.get_session_duration()
        return self._format_duration(duration)

    def is_active(self) -> bool:
        """Возвращает True, если сессия активна (игра запущена)."""
        return self._game_name is not None and self._start_time is not None

    def get_game_name(self) -> Optional[str]:
        """Возвращает название текущей игры или None, если сессия не активна."""
        return self._game_name

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """
        Форматирует количество секунд в строку HH:MM:SS.

        Args:
            seconds: количество секунд (неотрицательное целое).

        Returns:
            str: строка формата HH:MM:SS (например, "01:23:45").
        """
        if seconds < 0:
            seconds = 0
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"