"""
Главный модуль приложения GameDesk.

Нормальный режим: поиск ESP32, мониторинг игр, отправка данных и статистики.
Тестовый режим --dummy оставлен для отладки.
"""

import argparse
import logging
import random
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any

# По умолчанию Python не печатает INFO/WARNING в консоль, если не настроен
# logging.basicConfig() — из-за этого сообщения из telemetry.py ("LibreHardwareMonitor
# инициализирован успешно" / варнинги про отсутствие psutil-pythonnet) были не видны,
# а видна была только строка про ошибку (logger.error проходит через lastResort-handler).
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# Импорт модулей проекта
from packet_builder import PacketBuilder
from stats_manager import StatsManager
from serial_sender import SerialSender
from process_monitor import ProcessMonitor
from session_tracker import SessionTracker
from telemetry import TelemetryReader   # Phase 5: реальная телеметрия (LibreHardwareMonitor)
from hwinfo_reader import HWiNFOTelemetryReader  # приоритетный источник CPU/GPU/RAM (см. hwinfo_reader.py)

# ПРИМЕЧАНИЕ: раньше здесь был локальный get_telemetry() с random.randint(...),
# который использовался ВМЕСТО TelemetryReader (импорт которого был закомментирован).
# telemetry.py при этом был полностью реализован и рабочий, просто не подключён.
# Именно поэтому экран MONITOR показывал случайные, но неизменно "правдоподобные"
# числа вместо -1/реальных данных. TelemetryReader.get_telemetry() уже сам
# возвращает -1 по каждому параметру, если LibreHardwareMonitor недоступен —
# отдельная заглушка тут больше не нужна.


# ----------------------------------------------------------------------
# Нормальный режим (основной)
# ----------------------------------------------------------------------
def normal_mode() -> None:
    """
    Основной цикл работы с реальным ESP32.
    """
    print("[MAIN] GameDesk PC starting...")

    # 1. Инициализация модулей
    stats = StatsManager()          # загружает games.json
    sender = SerialSender()
    tracker = SessionTracker()
    builder = PacketBuilder()
    monitor = ProcessMonitor()
    telemetry_reader = TelemetryReader()   # Phase 5: реальная телеметрия (LibreHardwareMonitor)
    hwinfo_reader = HWiNFOTelemetryReader()  # приоритетный источник -- умеет CPU temp на AMD

    # 2. Основной цикл работы
    running = True
    last_status_time = 0            # для вывода статуса в консоль
    last_list_time = 0              # для отправки LIST-пакетов
    last_stats_time = 0             # для отправки STATS-пакетов (Phase 6)
    status_interval = 5             # сек
    list_interval = 30              # сек
    stats_interval = 10             # сек — сводная статистика обновляется чаще списка игр

    # Переменные для отслеживания текущей игры
    current_game: Optional[str] = None
    hwinfo_was_available: Optional[bool] = None  # для лога смены источника телеметрии

    print("[MAIN] Поиск ESP32...")

    while running:
        # ---- Поиск и подключение к устройству ----
        port = sender.find_and_connect()
        if not port:
            print("[SERIAL] Searching for GameDesk device...")
            time.sleep(5)
            continue

        print(f"[MAIN] Connected to ESP32 on {port}")

        # ---- Внутренний цикл отправки данных ----
        while running:
            try:
                # ---- Получение активной игры ----
                active_game = monitor.get_active_game()

                # ---- Управление сессией ----
                if active_game:
                    # Если игра изменилась или сессия не активна
                    if not tracker.is_active() or tracker.get_game_name() != active_game:
                        # Завершаем старую сессию, если она была.
                        #
                        # БАГ, который был здесь: get_game_name() вызывался ПОСЛЕ
                        # end_session(), а end_session() сама обнуляет _game_name
                        # внутри себя перед возвратом. В результате в stats.update_session()
                        # всегда прилетал None -> json.dump сериализовал ключ None
                        # в строку "null" в games.json, и туда же схлопывалась
                        # статистика вообще ВСЕХ игр подряд. Фикс: запоминаем имя
                        # игры ДО вызова end_session().
                        if tracker.is_active():
                            ended_game_name = tracker.get_game_name()
                            duration = tracker.end_session()
                            if duration is not None and duration > 0:
                                stats.update_session(ended_game_name, duration)
                                stats.save()
                        # Начинаем новую сессию
                        tracker.start_session(active_game)
                        current_game = active_game
                        print(f"[SESSION] Started: {active_game}")
                else:
                    # Если игры нет, завершаем сессию (тот же фикс, что и выше)
                    if tracker.is_active():
                        ended_game_name = tracker.get_game_name()
                        duration = tracker.end_session()
                        if duration is not None and duration > 0:
                            stats.update_session(ended_game_name, duration)
                            stats.save()
                        current_game = None
                        print("[SESSION] Stopped (no game)")

                # ---- Сбор телеметрии ----
                # Раньше тут был get_telemetry() с random.randint(...) — экран
                # MONITOR показывал случайные числа вместо реальных данных ПК.
                # Теперь два источника: HWiNFO (через Shared Memory, умеет
                # честно читать CPU temp даже на AMD Ryzen, где LibreHardware-
                # Monitor упирается в ограничения чтения SMU) и старый
                # LibreHardwareMonitor как запасной источник для полей, которые
                # HWiNFO почему-то не отдал (например если HWiNFO не запущен
                # или у него истёк 12-часовой лимит Shared Memory в free-версии
                # -- тогда просто откатываемся туда, где раньше уже работало).
                # LibreHardwareMonitor отдаёт float, протокол ждёт целое —
                # округляем сразу здесь. round(-1) == -1, так что отсутствие
                # данных не ломается.
                hw_telemetry = hwinfo_reader.get_telemetry()
                lhm_telemetry = telemetry_reader.get_telemetry()

                hwinfo_available_now = hwinfo_reader.get_last_error() is None
                if hwinfo_available_now != hwinfo_was_available:
                    if hwinfo_available_now:
                        print("[TELEMETRY] HWiNFO Shared Memory найдена — используется как приоритетный источник")
                    else:
                        print(f"[TELEMETRY] HWiNFO недоступна ({hwinfo_reader.get_last_error()}) — "
                              f"откат на LibreHardwareMonitor/psutil")
                    hwinfo_was_available = hwinfo_available_now

                def _pick(hw_value, lhm_value):
                    return hw_value if hw_value is not None and hw_value > 0 else lhm_value

                telemetry = {
                    "cpu": int(round(_pick(hw_telemetry["cpu_temp"], lhm_telemetry["cpu_temp"]))),
                    "gpu": int(round(_pick(hw_telemetry["gpu_temp"], lhm_telemetry["gpu_temp"]))),
                    "ram": int(round(_pick(hw_telemetry["ram_usage"], lhm_telemetry["ram_usage"]))),
                }

                # ---- Формирование и отправка пакета ----
                if tracker.is_active():
                    game_name = tracker.get_game_name()
                    session_str = tracker.get_session_str()
                    state = "RUNNING"
                    cpu = telemetry["cpu"]
                    gpu = telemetry["gpu"]
                    ram = telemetry["ram"]
                    fps = -1  # пока нет FPS

                    packet = builder.build_data_packet(
                        game=game_name,
                        session_str=session_str,
                        state=state,
                        fps=fps,
                        cpu=cpu,
                        gpu=gpu,
                        ram=ram
                    )
                else:
                    # Нет активной игры — раньше тут слался урезанный heartbeat
                    # <STATE=IDLE;HB=1> без полей CPU/GPU/RAM вообще. ESP32
                    # обновляет только те поля, которые реально пришли в пакете,
                    # поэтому MONITOR застывал на последних значениях от
                    # закрытой игры вместо живых показаний ПК. Телеметрия не
                    # привязана к тому, идёт ли игра — компьютер продолжает
                    # греться и грузить RAM независимо от этого, поэтому теперь
                    # шлём обычный DATA-пакет с GAME=NONE/STATE=IDLE, но с
                    # реальными CPU/GPU/RAM.
                    packet = builder.build_data_packet(
                        game="NONE",
                        session_str="00:00:00",
                        state="IDLE",
                        fps=-1,
                        cpu=telemetry["cpu"],
                        gpu=telemetry["gpu"],
                        ram=telemetry["ram"]
                    )

                # Отправка
                if not sender.send(packet):
                    print("[SERIAL] Send failed, connection lost")
                    break  # выходим из внутреннего цикла, ищем устройство заново

                now = time.time()

                # ---- Отправка STATS-пакета (Phase 6, каждые 10 сек) ----
                # Раньше такого пакета не существовало вообще — экран STATS
                # на ESP32 был жёстко зашит и никогда не получал реальных данных.
                # StatsManager.get_stats_summary() уже был реализован и рабочий,
                # его просто никто не вызывал.
                if now - last_stats_time >= stats_interval:
                    summary = stats.get_stats_summary()
                    stats_packet = builder.build_stats_packet(
                        weekly_sec=summary["weekly_total_sec"],
                        monthly_sec=summary["monthly_total_sec"],
                        total_games=summary["total_games"]
                    )
                    if not sender.send(stats_packet):
                        print("[SERIAL] Failed to send STATS packet, connection lost")
                        break
                    last_stats_time = now

                # ---- Отправка LIST-пакета (каждые 30 сек) ----
                if now - last_list_time >= list_interval:
                    recent = stats.get_recent_games(limit=10)
                    if recent:
                        # Преобразуем в формат для packet_builder
                        list_data = []
                        for game in recent:
                            list_data.append({
                                "name": game["name"],
                                "total_sec": game["total_time"],
                                "last_played": game["last_played"],
                                "weekly_sec": game["weekly_time"],
                                "monthly_sec": game["monthly_time"]
                            })
                        list_packet = builder.build_list_packet(list_data)
                        if not sender.send(list_packet):
                            print("[SERIAL] Failed to send LIST packet, connection lost")
                            break
                    last_list_time = now

                # ---- Вывод статуса в консоль (каждые 5 сек) ----
                if now - last_status_time >= status_interval:
                    if tracker.is_active():
                        status = (f"Active: {tracker.get_game_name()} | "
                                  f"Session: {tracker.get_session_str()} | "
                                  f"CPU: {telemetry['cpu']}C | "
                                  f"GPU: {telemetry['gpu']}C | "
                                  f"RAM: {telemetry['ram']}%")
                    else:
                        status = "Idle (no active game)"
                    print(f"[STATUS] {status}")
                    last_status_time = now

                # ---- Пауза 1 секунда ----
                time.sleep(1)

            except KeyboardInterrupt:
                running = False
                break
            except Exception as e:
                print(f"[MAIN] Unexpected error: {e}")
                time.sleep(1)

        # Если вышли из внутреннего цикла по потере соединения, продолжаем поиск
        if running:
            print("[SERIAL] Connection lost, searching again...")
            sender.disconnect()
            time.sleep(1)

    # ---- Завершение работы ----
    # Завершаем текущую сессию, если активна (тот же фикс: имя — до end_session())
    if tracker.is_active():
        ended_game_name = tracker.get_game_name()
        duration = tracker.end_session()
        if duration is not None and duration > 0:
            stats.update_session(ended_game_name, duration)
            stats.save()
            print(f"[SESSION] Final session saved: {ended_game_name} ({duration} sec)")

    # Отправить команду SHUTDOWN, чтобы ESP32 перешёл в WAITING
    if sender.is_connected():
        try:
            sender.send("<CMD=SHUTDOWN>")
            time.sleep(0.5)  # дать время ESP32 обработать
        except:
            pass

    sender.disconnect()
    telemetry_reader.close()
    print("[MAIN] GameDesk stopped.")


# ----------------------------------------------------------------------
# Тестовый режим --dummy (оставлен без изменений)
# ----------------------------------------------------------------------
def dummy_mode() -> None:
    """
    Тестовый режим для отладки без реального ESP32.
    """
    print("[DUMMY] Запуск тестового режима без ESP32")
    print("[DUMMY] Симуляция игровой сессии...")

    builder = PacketBuilder()
    stats = StatsManager()

    test_games = [
        {"name": "RDR2", "total_sec": 3600, "last_played": "2025-03-15", "weekly_sec": 1200, "monthly_sec": 4800},
        {"name": "CS2", "total_sec": 1800, "last_played": "2025-03-14", "weekly_sec": 900, "monthly_sec": 2700},
        {"name": "Cyberpunk 2077", "total_sec": 7200, "last_played": "2025-03-10", "weekly_sec": 0, "monthly_sec": 3600},
    ]

    current_game = None
    session_start = None
    state = "IDLE"
    game_switch_time = 30
    end_time = 60
    start_time = time.time()
    last_list_time = time.time()

    print("[DUMMY] Начинаем симуляцию... (нажмите Ctrl+C для выхода)")

    try:
        while True:
            elapsed = time.time() - start_time

            if elapsed < game_switch_time:
                if current_game != "RDR2":
                    current_game = "RDR2"
                    session_start = time.time()
                    state = "RUNNING"
                    print(f"[DUMMY] Игра начата: {current_game}")
            elif elapsed < end_time:
                if current_game != "CS2":
                    if session_start:
                        duration = int(time.time() - session_start)
                        print(f"[DUMMY] Сессия {current_game} завершена, длительность {duration} сек")
                        stats.update_session(current_game, duration)
                    current_game = "CS2"
                    session_start = time.time()
                    state = "RUNNING"
                    print(f"[DUMMY] Игра начата: {current_game}")
            else:
                if state != "IDLE":
                    if session_start:
                        duration = int(time.time() - session_start)
                        print(f"[DUMMY] Сессия {current_game} завершена, длительность {duration} сек")
                        stats.update_session(current_game, duration)
                    current_game = None
                    session_start = None
                    state = "IDLE"
                    print("[DUMMY] Игровая сессия завершена (IDLE)")

            if session_start:
                session_duration = int(time.time() - session_start)
                session_str = SessionTracker._format_duration(session_duration)
            else:
                session_str = "00:00:00"

            cpu = random.randint(50, 80) if state == "RUNNING" else -1
            gpu = random.randint(45, 75) if state == "RUNNING" else -1
            ram = random.randint(35, 55) if state == "RUNNING" else -1

            game_name = current_game if current_game else "NONE"
            packet = builder.build_data_packet(
                game=game_name,
                session_str=session_str,
                state=state,
                fps=-1,
                cpu=cpu,
                gpu=gpu,
                ram=ram
            )
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {packet}")

            if time.time() - last_list_time >= 15:
                list_packet = builder.build_list_packet(test_games)
                print(f"[{timestamp}] {list_packet}")
                last_list_time = time.time()

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[DUMMY] Тестовый режим остановлен пользователем.")


# ----------------------------------------------------------------------
# Точка входа
# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="GameDesk PC Application")
    parser.add_argument(
        "--dummy",
        action="store_true",
        help="Запуск в тестовом режиме без реального ESP32 (симуляция игровой сессии)"
    )
    args = parser.parse_args()

    if args.dummy:
        dummy_mode()
    else:
        normal_mode()


if __name__ == "__main__":
    main()