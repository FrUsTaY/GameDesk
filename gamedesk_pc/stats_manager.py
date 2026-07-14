"""
Модуль управления статистикой игр.

Обеспечивает загрузку, сохранение, обновление и сброс статистики в файле games.json.
"""

import json
import os
from datetime import datetime, date
from typing import Dict, List, Optional, Any

from config import STATS_FILE, WEEKLY_RESET_DAY, MONTHLY_RESET_DAY


class StatsManager:
    """Управление статистикой игр."""

    def __init__(self, filepath: str = STATS_FILE):
        """
        Инициализация менеджера статистики.

        Args:
            filepath: путь к файлу статистики (по умолчанию из config).
        """
        self.filepath = filepath
        self.data = self.load()

    def load(self) -> Dict[str, Any]:
        """
        Загружает данные из JSON-файла.

        Если файл отсутствует или повреждён, создаёт новую структуру.
        После загрузки проверяет необходимость сброса недельной/месячной статистики.

        Returns:
            Dict: словарь с данными (ключи: "games", "meta").
        """
        default_data = {
            "games": {},
            "meta": {
                "last_weekly_reset": date.today().isoformat(),
                "last_monthly_reset": date.today().isoformat()
            }
        }

        if not os.path.exists(self.filepath):
            self.data = default_data
            self.save()
            return self.data

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            # Файл повреждён – создаём новый
            print("[WARNING] Файл статистики повреждён. Создаётся новый.")
            self.data = default_data
            self.save()
            return self.data

        # Проверяем наличие обязательных разделов
        if "games" not in data:
            data["games"] = {}
        if "meta" not in data:
            data["meta"] = default_data["meta"]

        # Убеждаемся, что поля meta существуют
        if "last_weekly_reset" not in data["meta"]:
            data["meta"]["last_weekly_reset"] = default_data["meta"]["last_weekly_reset"]
        if "last_monthly_reset" not in data["meta"]:
            data["meta"]["last_monthly_reset"] = default_data["meta"]["last_monthly_reset"]

        self.data = data
        # Проверяем сбросы и сохраняем, если что-то изменилось
        changed = False
        if self._check_and_reset_weekly():
            changed = True
        if self._check_and_reset_monthly():
            changed = True
        if changed:
            self.save()
        return self.data

    def save(self) -> None:
        """Сохраняет текущие данные в JSON-файл."""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"[ERROR] Не удалось сохранить статистику: {e}")

    def update_session(self, game_name: str, duration_seconds: int) -> None:
        """
        Обновляет статистику после завершения игровой сессии.

        Добавляет игру, если её нет, увеличивает total_time, weekly_time, monthly_time,
        обновляет last_played (текущая дата) и session_count.

        Args:
            game_name: отображаемое название игры (из GAMES).
            duration_seconds: длительность сессии в секундах.
        """
        if duration_seconds <= 0:
            return  # не обновляем нулевые сессии

        # Защита от мусорных имён (например, если где-то выше по стеку случайно
        # передали None — как было в старом main.py, из-за чего в games.json
        # появлялся ключ "null": json.dump сериализует ключ-None в строку "null").
        # Без этой проверки такая запись молча создаётся и портит статистику.
        if not game_name or not isinstance(game_name, str) or game_name.strip().lower() in ("none", "null", ""):
            print(f"[WARNING] update_session: отклонено некорректное имя игры: {game_name!r}")
            return

        games = self.data["games"]
        if game_name not in games:
            games[game_name] = {
                "total_time": 0,
                "weekly_time": 0,
                "monthly_time": 0,
                "last_played": None,
                "session_count": 0
            }

        game_stats = games[game_name]
        game_stats["total_time"] += duration_seconds
        game_stats["weekly_time"] += duration_seconds
        game_stats["monthly_time"] += duration_seconds
        game_stats["last_played"] = date.today().isoformat()  # YYYY-MM-DD
        game_stats["session_count"] += 1

        self.save()

    def _check_and_reset_weekly(self) -> bool:
        """
        Проверяет, нужно ли обнулить недельную статистику.

        Сброс происходит, если сегодня понедельник (WEEKLY_RESET_DAY = 0)
        и дата последнего сброса не равна сегодняшней.

        Returns:
            bool: True, если сброс был выполнен, иначе False.
        """
        today = date.today()
        last_reset_str = self.data["meta"].get("last_weekly_reset")
        if last_reset_str is None:
            last_reset = date(2000, 1, 1)  # давно
        else:
            try:
                last_reset = datetime.fromisoformat(last_reset_str).date()
            except ValueError:
                last_reset = date(2000, 1, 1)

        # Проверяем, что сегодня понедельник (0) и последний сброс был не сегодня
        if today.weekday() == WEEKLY_RESET_DAY and last_reset != today:
            # Обнуляем weekly_time у всех игр
            for game in self.data["games"].values():
                game["weekly_time"] = 0
            self.data["meta"]["last_weekly_reset"] = today.isoformat()
            print(f"[STATS] Недельная статистика сброшена (понедельник {today})")
            return True
        return False

    def _check_and_reset_monthly(self) -> bool:
        """
        Проверяет, нужно ли обнулить месячную статистику.

        Сброс происходит, если сегодня 1-е число месяца (MONTHLY_RESET_DAY = 1)
        и дата последнего сброса не равна сегодняшней.

        Returns:
            bool: True, если сброс был выполнен, иначе False.
        """
        today = date.today()
        last_reset_str = self.data["meta"].get("last_monthly_reset")
        if last_reset_str is None:
            last_reset = date(2000, 1, 1)
        else:
            try:
                last_reset = datetime.fromisoformat(last_reset_str).date()
            except ValueError:
                last_reset = date(2000, 1, 1)

        # Проверяем, что сегодня 1-е число и последний сброс был не сегодня
        if today.day == MONTHLY_RESET_DAY and last_reset != today:
            for game in self.data["games"].values():
                game["monthly_time"] = 0
            self.data["meta"]["last_monthly_reset"] = today.isoformat()
            print(f"[STATS] Месячная статистика сброшена (1-е число {today})")
            return True
        return False

    # Публичные методы для внешнего использования (обёртки над внутренними)
    def check_and_reset_weekly(self) -> bool:
        """Публичный метод для ручного вызова проверки сброса недельной статистики."""
        return self._check_and_reset_weekly()

    def check_and_reset_monthly(self) -> bool:
        """Публичный метод для ручного вызова проверки сброса месячной статистики."""
        return self._check_and_reset_monthly()

    def get_recent_games(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Возвращает список последних игр, отсортированный по дате последнего запуска (свежие сверху).

        Игры без last_played (никогда не запускались) исключаются из списка.
        Количество записей ограничено параметром limit.

        Args:
            limit: максимальное количество записей (по умолчанию 10).

        Returns:
            List[Dict]: список словарей с ключами:
                - "name" (название игры)
                - "total_time" (общее время, сек)
                - "weekly_time" (время за неделю, сек)
                - "monthly_time" (время за месяц, сек)
                - "last_played" (дата в формате YYYY-MM-DD)
                - "session_count" (количество сессий)
        """
        games = self.data["games"]
        # Отбираем игры, у которых есть last_played
        valid_games = []
        for name, stats in games.items():
            if stats.get("last_played") is not None:
                valid_games.append({
                    "name": name,
                    "total_time": stats.get("total_time", 0),
                    "weekly_time": stats.get("weekly_time", 0),
                    "monthly_time": stats.get("monthly_time", 0),
                    "last_played": stats["last_played"],
                    "session_count": stats.get("session_count", 0)
                })

        # Сортируем по дате последнего запуска (убывание: свежие сверху)
        valid_games.sort(key=lambda x: x["last_played"], reverse=True)

        # Возвращаем первые limit записей
        return valid_games[:limit]

    def get_stats_summary(self) -> Dict[str, Any]:
        """
        Возвращает сводную статистику для экрана STATS.

        Returns:
            Dict с ключами:
                - "weekly_total_sec" (общее время за неделю по всем играм)
                - "monthly_total_sec" (общее время за месяц по всем играм)
                - "total_games" (общее количество уникальных игр)
        """
        games = self.data["games"]
        weekly_total = 0
        monthly_total = 0
        for stats in games.values():
            weekly_total += stats.get("weekly_time", 0)
            monthly_total += stats.get("monthly_time", 0)

        return {
            "weekly_total_sec": weekly_total,
            "monthly_total_sec": monthly_total,
            "total_games": len(games)
        }

    def get_game_stats(self, game_name: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает статистику для конкретной игры.

        Args:
            game_name: отображаемое название игры.

        Returns:
            Optional[Dict]: словарь со статистикой или None, если игра не найдена.
        """
        return self.data["games"].get(game_name)