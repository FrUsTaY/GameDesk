"""
Модуль отправки данных через Serial (COM-порт).

Обеспечивает обнаружение ESP32 по протоколу Handshake, подключение и отправку пакетов.
"""

import time
import serial
import serial.tools.list_ports
from typing import Optional

from config import SERIAL_BAUD, SERIAL_TIMEOUT, MAX_RATE_HZ, PING_TIMEOUT


class SerialSender:
    """Управление Serial-соединением с ESP32."""

    def __init__(self):
        self._port: Optional[str] = None
        self._ser: Optional[serial.Serial] = None
        self._connected = False
        self._last_send_time = 0.0

    def find_and_connect(self) -> Optional[str]:
        """
        Выполняет автоматический поиск ESP32 и сразу подключается к ней.

        Если устройство найдено, порт остаётся открытым для дальнейшей работы.
        Возвращает имя порта при успехе, иначе None.

        Returns:
            Optional[str]: имя порта, если устройство найдено и подключено, иначе None.
        """
        if self.is_connected():
            return self._port

        ports = serial.tools.list_ports.comports()
        if not ports:
            print("[SERIAL] Нет доступных COM-портов.")
            return None

        print(f"[SERIAL] Поиск ESP32 на {len(ports)} портах...")

        for port_info in ports:
            port_name = port_info.device
            print(f"[SERIAL] Проверка порта {port_name}...")

            ser = None
            try:
                ser = serial.Serial(
                    port=port_name,
                    baudrate=SERIAL_BAUD,
                    timeout=PING_TIMEOUT,
                    write_timeout=PING_TIMEOUT,
                    dsrdtr=False,
                    rtscts=False
                )
            except Exception as e:
                print(f"[SERIAL] Не удалось открыть {port_name}: {e}")
                continue

            try:
                # Принудительно отключаем DTR/RTS (это предотвращает сброс ESP32)
                ser.dtr = False
                ser.rts = False

                print("[SERIAL] Ожидание загрузки ESP32 (5 сек)...")
                time.sleep(5.0)

                ser.reset_input_buffer()
                ser.reset_output_buffer()

                # Делаем до 3 попыток
                for attempt in range(3):
                    print(f"[SERIAL] Отправка PING, попытка {attempt+1}/3...")
                    ser.write(b"<CMD=PING>\n")
                    ser.flush()
                    time.sleep(1.0)

                    # Читаем все доступные данные
                    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore').strip()

                    if "<CMD=PONG;DEVICE=GAMEDECK;VER=1>" in response:
                        print(f"[SERIAL] ESP32 найдена на порту {port_name}!")
                        # Сохраняем открытый порт
                        self._ser = ser
                        self._port = port_name
                        self._connected = True
                        # Даём время на стабилизацию после подключения
                        time.sleep(2.0)
                        return port_name
                    elif response:
                        print(f"[SERIAL] Получено: {response[:100]}...")
                    else:
                        print("[SERIAL] Ответ не получен")
                        time.sleep(0.5)

                print(f"[SERIAL] PONG не получен на {port_name} после 3 попыток")

            except Exception as e:
                print(f"[SERIAL] Ошибка при работе с портом {port_name}: {e}")
            finally:
                # Если подключение не удалось, закрываем порт
                if ser is not None and ser.is_open and ser != self._ser:
                    ser.close()

        print("[SERIAL] ESP32 не найдена ни на одном порту.")
        return None

    def disconnect(self) -> None:
        """Закрывает текущее Serial-соединение, если оно открыто."""
        if self._ser is not None and self._ser.is_open:
            try:
                self._ser.close()
                print(f"[SERIAL] Соединение с {self._port} закрыто.")
            except Exception as e:
                print(f"[SERIAL] Ошибка при закрытии порта: {e}")
        self._ser = None
        self._port = None
        self._connected = False
        self._last_send_time = 0.0

    def is_connected(self) -> bool:
        """Возвращает True, если соединение установлено и порт открыт."""
        return self._connected and self._ser is not None and self._ser.is_open

    def send(self, packet: str) -> bool:
        """
        Отправляет пакет данных через Serial.
        Добавляет символ новой строки в конец пакета.
        Ограничивает частоту отправки до MAX_RATE_HZ раз в секунду.
        При возникновении исключения соединение помечается как разорванное.
        Args:
            packet: строка пакета (без завершающего символа новой строки).
        Returns:
            bool: True, если отправка успешна, иначе False.
        """
        if not self.is_connected():
            return False

        current_time = time.time()
        min_interval = 1.0 / MAX_RATE_HZ
        time_since_last = current_time - self._last_send_time
        if time_since_last < min_interval:
            time.sleep(min_interval - time_since_last)

        try:
            data = packet + "\n"
            self._ser.write(data.encode('utf-8'))
            self._ser.flush()
            self._last_send_time = time.time()
            return True
        except Exception as e:
            print(f"[SERIAL] Ошибка отправки: {e}")
            # Соединение разорвано – помечаем как отключённое
            self._connected = False
            if self._ser:
                try:
                    self._ser.close()
                except Exception:
                    pass
                self._ser = None
            self._port = None
            return False