"""
Модуль формирования пакетов для отправки на ESP32.

Обеспечивает создание одиночных пакетов данных, heartbeat, PING и групповых LIST-пакетов.
"""

import re
from typing import List, Dict, Any


class PacketBuilder:
    """
    Построитель пакетов по протоколу GameDesk.

    Управляет нумерацией пакетов для вставки VER и DEVICE в каждый пятый пакет.
    """

    def __init__(self):
        """Инициализация счётчика пакетов."""
        self._packet_counter = 0

    @staticmethod
    def _sanitize_string(value: str) -> str:
        """
        Очищает строку от запрещённых символов: ; < > =

        Заменяет их на пробел.

        Args:
            value: исходная строка.

        Returns:
            str: очищенная строка.
        """
        if not isinstance(value, str):
            value = str(value)
        # Удаляем символы, которые могут нарушить парсинг пакета
        return re.sub(r'[;<>=]', ' ', value).strip()

    @staticmethod
    def _format_duration_hhmm(seconds: int) -> str:
        """
        Преобразует секунды в строку "HH:MM" (часы и минуты, без секунд).

        Args:
            seconds: количество секунд (неотрицательное целое).

        Returns:
            str: строка формата "HH:MM" (например, "01:23").
        """
        if seconds < 0:
            seconds = 0
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

    def build_data_packet(
            self,
            game: str,
            session_str: str,
            state: str,
            fps: int,
            cpu: int,
            cpu_usage: int,
            gpu: int,
            gpu_usage: int,
            ram: int
    ) -> str:
        """
        Формирует одиночный пакет с данными о текущей игре и телеметрии.

        Поля:
            GAME (название игры)
            SESSION (время сессии HH:MM:SS)
            STATE (RUNNING|IDLE|OFFLINE)
            FPS (число или -1)
            CPU (число или -1)
            CU (число или -1)
            GPU (число или -1)
            GU (число или -1)
            RAM (число или -1)

        VER и DEVICE добавляются в каждый 5-й пакет (счётчик внутри класса),
        в остальных опускаются.

        Args:
            game: отображаемое название игры.
            session_str: строка времени сессии в формате HH:MM:SS.
            state: состояние (RUNNING, IDLE, OFFLINE).
            fps: FPS или -1.
            cpu: температура CPU или -1.
            gpu: температура GPU или -1.
            ram: использование RAM в % или -1.

        Returns:
            str: готовый пакет для отправки в формате <...>.
        """
        self._packet_counter += 1

        # Очищаем имя игры от запрещённых символов
        game_safe = self._sanitize_string(game)

        # Формируем базовый набор полей (без VER и DEVICE)
        fields = {
            "GAME": game_safe,
            "SESSION": session_str,
            "STATE": state,
            "FPS": str(fps),
            "CPU": str(cpu),
            "CU": str(cpu_usage),
            "GPU": str(gpu),
            "GU": str(gpu_usage),
            "RAM": str(ram)
        }

        # Добавляем VER и DEVICE в первый пакет после подключения и затем в каждый
        # 5-й (ТЗ §6.2: "VER и DEVICE обязательны в первом пакете, отправляемом
        # после установки соединения"). Раньше проверялось только "% 5 == 0",
        # а счётчик стартует с 1 после первого инкремента — то есть VER/DEVICE
        # не попадали в самый первый пакет вообще.
        if self._packet_counter == 1 or self._packet_counter % 5 == 0:
            fields_with_ver = {
                "VER": "1",
                "DEVICE": "GAMEDECK",
                **fields
            }
            packet_body = ";".join(f"{k}={v}" for k, v in fields_with_ver.items())
        else:
            packet_body = ";".join(f"{k}={v}" for k, v in fields.items())

        packet = f"<{packet_body}>"

        # Проверяем длину пакета (максимум 256 байт)
        if len(packet) > 256:
            # Укорачиваем название игры, если оно слишком длинное
            # Удаляем GAME=... и вставляем урезанное значение
            # Находим позицию GAME=
            game_prefix = "GAME="
            start = packet.find(game_prefix)
            if start != -1:
                # Извлекаем остаток пакета до первого ';' после GAME=
                end = packet.find(";", start + len(game_prefix))
                if end == -1:
                    end = len(packet) - 1  # конец перед >
                # Имя игры — это часть между GAME= и ;
                old_game_value = packet[start + len(game_prefix):end]
                # Обрезаем до разумной длины, чтобы общая длина стала ≤ 256
                # Оставляем запас на остальные поля, но упростим: обрезаем до 20 символов
                max_game_len = 20
                if len(old_game_value) > max_game_len:
                    new_game_value = old_game_value[:max_game_len]
                    # Заменяем в строке
                    packet = packet[:start + len(game_prefix)] + new_game_value + packet[end:]
                    # Если всё равно длиннее, просто обрезаем до 256 символов, но сохраняем '>'
                    if len(packet) > 256:
                        packet = packet[:255] + ">"

        return packet

    def build_heartbeat(self) -> str:
        """
        Формирует heartbeat-пакет для отправки в режиме IDLE.

        Returns:
            str: пакет <STATE=IDLE;HB=1>
        """
        return "<STATE=IDLE;HB=1>"

    def build_ping(self) -> str:
        """
        Формирует PING-команду для обнаружения устройства (Handshake).

        Returns:
            str: пакет <CMD=PING>
        """
        return "<CMD=PING>"

    def build_stats_packet(self, weekly_sec: int, monthly_sec: int, total_games: int) -> str:
        """
        Формирует сводный пакет статистики для экрана STATS (Phase 6).

        Раньше такого пакета не существовало вовсе — экран STATS на ESP32
        был жёстко зашит ("Week: 14:32", "Games: 8") и никогда не получал
        реальных данных с ПК. StatsManager.get_stats_summary() всё это время
        честно считал агрегаты, но их было некуда отправлять.

        Формат: <STATS;WEEK=HH:MM;MONTH=HH:MM;GAMES=N>

        Args:
            weekly_sec: суммарное время за неделю по всем играм, сек.
            monthly_sec: суммарное время за месяц по всем играм, сек.
            total_games: количество уникальных игр в games.json.

        Returns:
            str: готовый пакет.
        """
        week_str = self._format_duration_hhmm(weekly_sec)
        month_str = self._format_duration_hhmm(monthly_sec)
        return f"<STATS;WEEK={week_str};MONTH={month_str};GAMES={total_games}>"

    def build_list_packet(self, games: List[Dict[str, Any]]) -> str:
        """
        Формирует групповой LIST-пакет для экрана RECENT GAMES.

        Входной список содержит словари с ключами:
            name (название игры),
            total_sec (общее время в секундах),
            last_played (дата в формате YYYY-MM-DD),
            weekly_sec (время за неделю, сек),
            monthly_sec (время за месяц, сек)

        На выходе:
            <LIST=RECENT;COUNT=N>
            <GAME=...;TOTAL=HH:MM;LAST=YYYY-MM-DD;WEEK=HH:MM;MONTH=HH:MM>
            ...
            </LIST>

        Количество записей ограничено 10.
        Каждое имя очищается от запрещённых символов.
        Максимальная общая длина пакета — 512 байт.
        В случае превышения список урезается до тех пор, пока не влезет.

        Args:
            games: список игр для включения в пакет.

        Returns:
            str: готовый LIST-пакет.
        """
        # Ограничиваем до 10 игр
        games = games[:10]

        # Формируем заголовок списка
        header = f"<LIST=RECENT;COUNT={len(games)}>"
        footer = "</LIST>"

        # Формируем строки для каждой игры
        lines = []
        for game_data in games:
            name = self._sanitize_string(game_data.get("name", "Unknown"))
            total_sec = game_data.get("total_sec", 0)
            last_played = game_data.get("last_played", "1970-01-01")
            weekly_sec = game_data.get("weekly_sec", 0)
            monthly_sec = game_data.get("monthly_sec", 0)

            # Форматируем время в HH:MM
            total_str = self._format_duration_hhmm(total_sec)
            weekly_str = self._format_duration_hhmm(weekly_sec)
            monthly_str = self._format_duration_hhmm(monthly_sec)

            # Строка игры
            line = f"<GAME={name};TOTAL={total_str};LAST={last_played};WEEK={weekly_str};MONTH={monthly_str}>"
            lines.append(line)

        # Собираем полный пакет
        packet = header + "".join(lines) + footer

        # Проверяем длину, если превышает 512 байт — урезаем список
        if len(packet) > 512:
            # Удаляем последние игры, пока не влезет
            while len(lines) > 0 and len(packet) > 512:
                lines.pop()
                # Обновляем заголовок
                header = f"<LIST=RECENT;COUNT={len(lines)}>"
                packet = header + "".join(lines) + footer

        return packet