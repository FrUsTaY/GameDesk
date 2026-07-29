# ====================================================================
# telemetry.py — модуль сбора телеметрии (CPU/GPU/RAM)
# Проект: GameDesk
# Версия: 1.0
# Дата: 2026-07-02
# ====================================================================

import time
import logging
from typing import Dict, Optional, Union

# Настройка логирования
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------
# Попытка импорта библиотек для телеметрии
# --------------------------------------------------------------------
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil не установлен, RAM usage будет недоступен при падении LibreHardwareMonitor")

try:
    import clr
    from System import Array
    from System.Collections.Generic import List
    CLR_AVAILABLE = True
except ImportError:
    CLR_AVAILABLE = False
    logger.warning("pythonnet (clr) не установлен, LibreHardwareMonitor не будет работать")


class TelemetryReader:
    """
    Класс для сбора телеметрии с использованием LibreHardwareMonitor.
    Данные кэшируются на 2 секунды.
    При недоступности возвращаются -1 для всех значений.
    """

    def __init__(self, lib_path: Optional[str] = None):
        """
        Инициализация.
        :param lib_path: путь к папке с LibreHardwareMonitorLib.dll.
                         Если None, будет поиск в стандартных местах.
        """
        self._cache: Dict[str, Union[int, float]] = {
            'cpu_temp': -1,
            'cpu_usage': -1,
            'gpu_temp': -1,
            'gpu_usage': -1,
            'ram_usage': -1
        }
        self._cache_time: float = 0
        self._cache_ttl: float = 2.0  # секунды

        self._lib_path = lib_path
        self._computer = None
        self._is_initialized = False

        # Пытаемся инициализировать LibreHardwareMonitor
        if CLR_AVAILABLE:
            try:
                self._init_lhm()
            except Exception as e:
                logger.error(f"Ошибка инициализации LibreHardwareMonitor: {e}")
                self._is_initialized = False
        else:
            logger.warning("LibreHardwareMonitor не доступен (нет pythonnet)")

    # --------------------------------------------------------------------
    # Инициализация LibreHardwareMonitor
    # --------------------------------------------------------------------
    def _init_lhm(self) -> None:
        """Загружает LibreHardwareMonitorLib и создаёт объект Computer."""
        import clr
        import sys
        import os

        # Поиск пути к библиотеке
        if self._lib_path is None:
            # Попробуем найти в текущей папке и в папке с программой
            possible_paths = [
                os.getcwd(),
                os.path.dirname(sys.executable),
                os.path.join(os.getcwd(), 'LibreHardwareMonitor'),
                os.path.join(os.path.dirname(sys.executable), 'LibreHardwareMonitor'),
            ]
            for path in possible_paths:
                dll_path = os.path.join(path, 'LibreHardwareMonitorLib.dll')
                if os.path.exists(dll_path):
                    self._lib_path = path
                    break
            else:
                raise FileNotFoundError("LibreHardwareMonitorLib.dll не найдена")

        # Добавляем ссылку на сборку
        clr.AddReference(os.path.join(self._lib_path, 'LibreHardwareMonitorLib.dll'))

        # Импортируем нужные пространства имён
        from LibreHardwareMonitor import Hardware

        # Создаём объект Computer и открываем доступ к сенсорам
        self._computer = Hardware.Computer()
        self._computer.IsCpuEnabled = True
        self._computer.IsGpuEnabled = True
        self._computer.IsMemoryEnabled = True
        self._computer.Open()

        self._is_initialized = True
        logger.info("LibreHardwareMonitor инициализирован успешно")

    # --------------------------------------------------------------------
    # Основной метод получения телеметрии
    # --------------------------------------------------------------------
    def get_telemetry(self) -> Dict[str, Union[int, float]]:
        """
        Возвращает словарь с ключами:
          cpu_temp, gpu_temp, ram_usage (int или float, в случае ошибки -1)
        Данные кэшируются на 2 секунды.
        """
        now = time.time()
        if (now - self._cache_time) < self._cache_ttl:
            return self._cache

        # Если библиотека не инициализирована, возвращаем заглушку
        if not self._is_initialized or not CLR_AVAILABLE:
            self._cache = {
                'cpu_temp': -1, 'cpu_usage': -1,
                'gpu_temp': -1, 'gpu_usage': -1,
                'ram_usage': -1, 'fps': -1
            }
            # Fallback for CPU usage via psutil if LHM is not available
            if PSUTIL_AVAILABLE:
                try:
                    self._cache['cpu_usage'] = psutil.cpu_percent(interval=None)
                except Exception:
                    pass
            self._cache_time = now
            return self._cache

        try:
            cpu_temp = self._get_cpu_temp()
            cpu_usage = self._get_cpu_usage()
            gpu_temp = self._get_gpu_temp()
            gpu_usage = self._get_gpu_usage()
            ram_usage = self._get_ram_usage()

            # Fallback for CPU usage via psutil
            if (cpu_usage is None or cpu_usage < 0) and PSUTIL_AVAILABLE:
                try:
                    cpu_usage = psutil.cpu_percent(interval=None)
                except Exception:
                    pass

            self._cache = {
                'cpu_temp': cpu_temp if cpu_temp is not None else -1,
                'cpu_usage': cpu_usage if cpu_usage is not None else -1,
                'gpu_temp': gpu_temp if gpu_temp is not None else -1,
                'gpu_usage': gpu_usage if gpu_usage is not None else -1,
                'ram_usage': ram_usage if ram_usage is not None else -1,
                'fps': -1 # LHM doesn't provide FPS
            }
        except Exception as e:
            logger.error(f"Ошибка при сборе телеметрии: {e}")
            self._cache = {
                'cpu_temp': -1, 'cpu_usage': -1,
                'gpu_temp': -1, 'gpu_usage': -1,
                'ram_usage': -1, 'fps': -1
            }

        self._cache_time = now
        return self._cache

    # --------------------------------------------------------------------
    # Приватные методы получения конкретных показателей
    # --------------------------------------------------------------------
    @staticmethod
    def _is_valid_temp(value) -> bool:
        """
        Проверяет, похоже ли значение на реальную температуру.

        LibreHardwareMonitor иногда отдаёт Value = 0 вместо null для сенсора,
        который физически не даёт показаний (маршалинг Nullable<float> через
        pythonnet, либо сенсор ещё не "прогрелся" сразу после Open()). Ноутбук
        под нагрузкой никогда не имеет реальные 0°C, поэтому 0 и None тут
        трактуются одинаково — как "данных нет".
        """
        return value is not None and value > 0

    def _get_cpu_temp(self) -> Optional[float]:
        """Возвращает температуру CPU или None."""
        if not self._is_initialized:
            return None
        try:
            from LibreHardwareMonitor import Hardware
            fallback_value = None
            for hardware in self._computer.Hardware:
                # Проверяем, что это CPU (обычно тип Cpu)
                if hardware.HardwareType == Hardware.HardwareType.Cpu:
                    hardware.Update()
                    for sensor in hardware.Sensors:
                        # Ищем сенсор температуры с подходящим именем
                        if sensor.SensorType == Hardware.SensorType.Temperature:
                            value = sensor.Value
                            if not self._is_valid_temp(value):
                                # 0/None -- пропускаем, а не отдаём как реальную температуру
                                continue
                            name_lower = sensor.Name.lower()
                            if 'cpu package' in name_lower or 'package' in name_lower:
                                return value
                            if fallback_value is None:
                                fallback_value = value
                    if fallback_value is not None:
                        return fallback_value
            return None
        except Exception as e:
            logger.debug(f"Ошибка получения температуры CPU: {e}")
            return None

    def _get_cpu_usage(self) -> Optional[float]:
        """Возвращает общую загрузку CPU или None."""
        if not self._is_initialized:
            return None
        try:
            from LibreHardwareMonitor import Hardware
            fallback_value = None
            for hardware in self._computer.Hardware:
                if hardware.HardwareType == Hardware.HardwareType.Cpu:
                    hardware.Update()
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == Hardware.SensorType.Load:
                            value = sensor.Value
                            if not self._is_valid_temp(value): # it checks if > 0
                                continue
                            name_lower = sensor.Name.lower()
                            if 'total' in name_lower or 'cpu total' in name_lower:
                                return value
                            if fallback_value is None:
                                fallback_value = value
                    if fallback_value is not None:
                        return fallback_value
            return None
        except Exception as e:
            logger.debug(f"Ошибка получения загрузки CPU: {e}")
            return None

    def _get_gpu_temp(self) -> Optional[float]:
        """Возвращает температуру GPU или None."""
        if not self._is_initialized:
            return None
        try:
            from LibreHardwareMonitor import Hardware
            fallback_value = None
            for hardware in self._computer.Hardware:
                # Проверяем, что это GPU (тип GpuNvidia, GpuAmd или GpuIntel)
                if hardware.HardwareType in (
                    Hardware.HardwareType.GpuNvidia,
                    Hardware.HardwareType.GpuAmd,
                    Hardware.HardwareType.GpuIntel
                ):
                    hardware.Update()
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == Hardware.SensorType.Temperature:
                            value = sensor.Value
                            if not self._is_valid_temp(value):
                                continue
                            name_lower = sensor.Name.lower()
                            if 'gpu core' in name_lower or 'gpu' in name_lower:
                                return value
                            if fallback_value is None:
                                fallback_value = value
                    if fallback_value is not None:
                        return fallback_value
            return None
        except Exception as e:
            logger.debug(f"Ошибка получения температуры GPU: {e}")
            return None

    def _get_gpu_usage(self) -> Optional[float]:
        """Возвращает загрузку GPU (Core) или None."""
        if not self._is_initialized:
            return None
        try:
            from LibreHardwareMonitor import Hardware
            fallback_value = None
            for hardware in self._computer.Hardware:
                if hardware.HardwareType in (
                    Hardware.HardwareType.GpuNvidia,
                    Hardware.HardwareType.GpuAmd,
                    Hardware.HardwareType.GpuIntel
                ):
                    hardware.Update()
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == Hardware.SensorType.Load:
                            value = sensor.Value
                            if not self._is_valid_temp(value):
                                continue
                            name_lower = sensor.Name.lower()
                            if 'gpu core' in name_lower or 'core' in name_lower:
                                return value
                            if fallback_value is None:
                                fallback_value = value
                    if fallback_value is not None:
                        return fallback_value
            return None
        except Exception as e:
            logger.debug(f"Ошибка получения загрузки GPU: {e}")
            return None

    def _get_ram_usage(self) -> Optional[float]:
        """
        Возвращает использование RAM в процентах.
        Сначала пытается через LibreHardwareMonitor (сенсор Load с Memory),
        если не получается — использует psutil.
        """
        if self._is_initialized:
            try:
                from LibreHardwareMonitor import Hardware
                fallback_value = None
                for hardware in self._computer.Hardware:
                    # Память может быть отдельным устройством. На некоторых системах
                    # LibreHardwareMonitor отдаёт ДВА объекта Memory одновременно:
                    # "Total Memory" (физическая RAM) и "Virtual Memory" (RAM + файл
                    # подкачки вместе, число всегда выше и не то, что обычно значит
                    # "загрузка RAM"). Раньше код брал первый попавшийся объект по
                    # порядку перечисления .NET, что могло случайно вернуть
                    # Virtual Memory вместо физической RAM. Теперь явно предпочитаем
                    # хардвер с именем "Total Memory".
                    if hardware.HardwareType == Hardware.HardwareType.Memory:
                        hardware.Update()
                        hw_name_lower = hardware.Name.lower()
                        for sensor in hardware.Sensors:
                            if sensor.SensorType == Hardware.SensorType.Load:
                                if 'total' in hw_name_lower:
                                    return sensor.Value
                                if fallback_value is None:
                                    fallback_value = sensor.Value
                if fallback_value is not None:
                    return fallback_value
            except Exception as e:
                logger.debug(f"Ошибка получения RAM через LibreHardwareMonitor: {e}")

        # Запасной вариант через psutil
        if PSUTIL_AVAILABLE:
            try:
                mem = psutil.virtual_memory()
                return mem.percent
            except Exception as e:
                logger.debug(f"Ошибка получения RAM через psutil: {e}")
        return None

    # --------------------------------------------------------------------
    # Закрытие ресурсов
    # --------------------------------------------------------------------
    def close(self) -> None:
        """Закрывает соединение с LibreHardwareMonitor."""
        if self._computer is not None:
            try:
                self._computer.Close()
            except Exception:
                pass
            self._computer = None
            self._is_initialized = False