"""
Главный модуль приложения GameDesk (System Tray Version).
"""

import argparse
import logging
import random
import sys
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any

import tkinter as tk
import pystray
from PIL import Image

# Импорт модулей проекта
from packet_builder import PacketBuilder
from stats_manager import StatsManager
from serial_sender import SerialSender
from process_monitor import ProcessMonitor
from session_tracker import SessionTracker
from telemetry import TelemetryReader
from hwinfo_reader import HWiNFOTelemetryReader
import autostart
from gui import SettingsWindow

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

class GameDeskApp:
    def __init__(self):
        self.running = True
        self.monitoring_active = False  # Флаг: работает ли COM/мониторинг
        self.monitor_thread = None
        self.stop_event = threading.Event()

        self.stats = StatsManager()

        self.tray_icon = None
        self.settings_window = None
        self.tk_root = None

    def start_monitoring(self):
        if self.monitoring_active:
            return
        self.monitoring_active = True
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self._update_tray_menu()

    def stop_monitoring(self):
        if not self.monitoring_active:
            return
        self.monitoring_active = False
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        self._update_tray_menu()

    def _monitoring_loop(self):
        """Фоновый поток для связи с ESP32 и телеметрии."""
        logging.info("Starting monitoring loop...")
        sender = SerialSender()
        tracker = SessionTracker()
        builder = PacketBuilder()
        monitor = ProcessMonitor()
        telemetry_reader = TelemetryReader()
        hwinfo_reader = HWiNFOTelemetryReader()

        last_status_time = 0
        last_list_time = 0
        last_stats_time = 0
        status_interval = 5
        list_interval = 30
        stats_interval = 10
        hwinfo_was_available = None

        while not self.stop_event.is_set():
            port = sender.find_and_connect()
            if not port:
                if self.stop_event.wait(timeout=5.0):
                    break
                continue

            logging.info(f"Connected to ESP32 on {port}")

            while not self.stop_event.is_set():
                try:
                    active_game = monitor.get_active_game()

                    if active_game:
                        if not tracker.is_active() or tracker.get_game_name() != active_game:
                            if tracker.is_active():
                                ended_game_name = tracker.get_game_name()
                                duration = tracker.end_session()
                                if duration is not None and duration > 0:
                                    self.stats.update_session(ended_game_name, duration)
                                    self.stats.save()
                            tracker.start_session(active_game)
                            logging.info(f"[SESSION] Started: {active_game}")
                    else:
                        if tracker.is_active():
                            ended_game_name = tracker.get_game_name()
                            duration = tracker.end_session()
                            if duration is not None and duration > 0:
                                self.stats.update_session(ended_game_name, duration)
                                self.stats.save()
                            logging.info("[SESSION] Stopped (no game)")

                    hw_telemetry = hwinfo_reader.get_telemetry()
                    lhm_telemetry = telemetry_reader.get_telemetry()

                    hwinfo_available_now = hwinfo_reader.get_last_error() is None
                    if hwinfo_available_now != hwinfo_was_available:
                        hwinfo_was_available = hwinfo_available_now

                    def _pick(hw_value, lhm_value):
                        return hw_value if hw_value is not None and hw_value > 0 else lhm_value

                    telemetry = {
                        "cpu": int(round(_pick(hw_telemetry["cpu_temp"], lhm_telemetry["cpu_temp"]))),
                        "gpu": int(round(_pick(hw_telemetry["gpu_temp"], lhm_telemetry["gpu_temp"]))),
                        "ram": int(round(_pick(hw_telemetry["ram_usage"], lhm_telemetry["ram_usage"]))),
                    }

                    if tracker.is_active():
                        game_name = tracker.get_game_name()
                        session_str = tracker.get_session_str()
                        packet = builder.build_data_packet(
                            game=game_name,
                            session_str=session_str,
                            state="RUNNING",
                            fps=-1,
                            cpu=telemetry["cpu"],
                            gpu=telemetry["gpu"],
                            ram=telemetry["ram"]
                        )
                    else:
                        packet = builder.build_data_packet(
                            game="NONE",
                            session_str="00:00:00",
                            state="IDLE",
                            fps=-1,
                            cpu=telemetry["cpu"],
                            gpu=telemetry["gpu"],
                            ram=telemetry["ram"]
                        )

                    if not sender.send(packet):
                        logging.warning("Send failed, connection lost")
                        break

                    now = time.time()
                    if now - last_stats_time >= stats_interval:
                        summary = self.stats.get_stats_summary()
                        stats_packet = builder.build_stats_packet(
                            weekly_sec=summary["weekly_total_sec"],
                            monthly_sec=summary["monthly_total_sec"],
                            total_games=summary["total_games"]
                        )
                        if not sender.send(stats_packet):
                            break
                        last_stats_time = now

                    if now - last_list_time >= list_interval:
                        recent = self.stats.get_recent_games(limit=10)
                        if recent:
                            list_data = [{"name": g["name"], "total_sec": g["total_time"], "last_played": g["last_played"], "weekly_sec": g["weekly_time"], "monthly_sec": g["monthly_time"]} for g in recent]
                            list_packet = builder.build_list_packet(list_data)
                            if not sender.send(list_packet):
                                break
                        last_list_time = now

                    if self.stop_event.wait(timeout=1.0):
                        break

                except Exception as e:
                    logging.error(f"Unexpected error in monitoring: {e}")
                    time.sleep(1)

            if not self.stop_event.is_set():
                sender.disconnect()
                time.sleep(1)

        # Cleanup on stop
        if tracker.is_active():
            ended_game_name = tracker.get_game_name()
            duration = tracker.end_session()
            if duration is not None and duration > 0:
                self.stats.update_session(ended_game_name, duration)
                self.stats.save()

        if sender.is_connected():
            try:
                sender.send("<CMD=SHUTDOWN>")
                time.sleep(0.5)
            except:
                pass
        sender.disconnect()
        telemetry_reader.close()
        logging.info("Monitoring loop stopped.")

    def show_settings(self):
        if self.monitoring_active:
            # Нельзя редактировать игры, пока работает мониторинг
            return

        if self.settings_window is None:
            self.settings_window = SettingsWindow(self.tk_root, self.stats, self._on_settings_closed)
            self.settings_window.protocol("WM_DELETE_WINDOW", self.settings_window.on_close)
        else:
            self.settings_window.lift()

    def _on_settings_closed(self):
        self.settings_window = None

    def toggle_autostart(self, icon, item):
        current = autostart.is_autostart_enabled()
        autostart.set_autostart(not current)

    def on_quit(self, icon, item):
        self.stop_monitoring()
        self.running = False
        icon.stop()
        if self.tk_root:
            self.tk_root.quit()

    def _create_image(self):
        # Если есть icon.ico, загружаем, иначе генерируем простую
        try:
            import os
            # Ищем иконку рядом с exe или в текущей папке
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_path, 'icon.ico')
            if not os.path.exists(icon_path):
                # Fallback для запуска из корня проекта
                icon_path = os.path.join(os.path.dirname(base_path), 'icon.ico')

            if os.path.exists(icon_path):
                return Image.open(icon_path)
        except Exception:
            pass

        # Генерация запасной иконки (синий квадрат)
        image = Image.new('RGB', (64, 64), color=(0, 100, 255))
        return image

    def _update_tray_menu(self):
        if not self.tray_icon:
            return

        is_auto = autostart.is_autostart_enabled()

        menu = pystray.Menu(
            pystray.MenuItem("Старт", lambda icon, item: self.start_monitoring(), enabled=not self.monitoring_active),
            pystray.MenuItem("Стоп", lambda icon, item: self.stop_monitoring(), enabled=self.monitoring_active),
            pystray.MenuItem("Управление играми", lambda icon, item: self.tk_root.after(0, self.show_settings), enabled=not self.monitoring_active),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Автозапуск с Windows", self.toggle_autostart, checked=lambda item: autostart.is_autostart_enabled()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self.on_quit)
        )
        self.tray_icon.menu = menu

    def run(self):
        # Инициализация скрытого Tkinter (используется только для создания окон настроек)
        self.tk_root = tk.Tk()
        self.tk_root.withdraw() # Скрываем главное окно

        # Инициализация Pystray
        self.tray_icon = pystray.Icon("GameDesk", self._create_image(), "GameDesk PC")
        self._update_tray_menu()

        # Запускаем трей в отдельном потоке (pystray.run блокирующий)
        def tray_thread():
            self.tray_icon.run()

        t = threading.Thread(target=tray_thread, daemon=True)
        t.start()

        # По умолчанию сразу запускаем мониторинг
        self.start_monitoring()

        # Главный цикл Tkinter для обработки событий GUI (окон)
        while self.running:
            try:
                self.tk_root.update_idletasks()
                self.tk_root.update()
            except tk.TclError:
                break
            time.sleep(0.05)


def dummy_mode():
    print("[DUMMY] Not supported in Tray version.")
    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description="GameDesk PC Application")
    parser.add_argument("--dummy", action="store_true", help="Test mode (Not supported in Tray GUI)")
    args = parser.parse_args()

    if args.dummy:
        dummy_mode()
    else:
        app = GameDeskApp()
        app.run()


if __name__ == "__main__":
    main()
