# ====================================================================
# hwinfo_reader.py -- чтение сенсоров из Shared Memory HWiNFO (Windows)
# Проект: GameDesk
# ====================================================================
#
# Формат структуры Shared Memory официально не документирован HWiNFO
# (спецификация закрыта и выдаётся разработчиком по отдельному запросу
# для одобренных сторонних приложений). Используемая здесь раскладка
# полей -- это community reverse-engineering формата (структура
# стабильна с версии 6.40 и используется несколькими независимыми
# реализациями на C#/C++, в т.ч. Hwinfo.SharedMemory.Net).
#
# ВАЖНО: этот модуль только ЧИТАЕТ уже опубликованную HWiNFO область
# памяти через стандартный Windows API (OpenFileMapping/MapViewOfFile).
# Сам HWiNFO не патчится, не декомпилируется, не реверсится -- это
# прямо запрещено его лицензией. Чтение отдельно опубликованных данных
# через официальный Windows IPC-механизм таким запретом не является --
# это ровно то же самое, что делают Rainmeter/RTSS/MSI Afterburner.
#
# ТРЕБОВАНИЯ на стороне пользователя:
#   1. HWiNFO должен быть запущен (можно в режиме "Sensors only")
#   2. В настройках HWiNFO включено "Shared Memory Support"
#      (правый клик по иконке в трее -> Settings -> General)
#   3. В БЕСПЛАТНОЙ версии HWiNFO это работает максимум 12 часов подряд,
#      затем функция автоматически отключается и требует, чтобы
#      пользователь вручную включил её заново в настройках HWiNFO.
#      Это ограничение самого HWiNFO, не наш код.
# ====================================================================

import ctypes
import ctypes.wintypes
import logging
import struct
import time
from typing import Dict, List, Optional, Union

logger = logging.getLogger(__name__)

SHARED_MEM_NAMES = [
    "Global\\HWiNFO_SENS_SM2",  # обычный случай (в т.ч. если GameDesk запущен от админа)
    "HWiNFO_SENS_SM2",          # запасной вариант без Global-namespace
]

HEADER_MAGIC = 0x53695748  # multi-char literal 'SiWH' как его компилирует MSVC

# --------------------------------------------------------------------
# Раскладка структур (все struct упакованы без выравнивания, поэтому
# используем "<" -- little-endian, без паддинга между полями)
# --------------------------------------------------------------------

# magic, version, version2, last_update(int64),
# sensor_section_offset, sensor_element_size, sensor_element_count,
# entry_section_offset, entry_element_size, entry_element_count
HEADER_FORMAT = "<IIIqIIIIII"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 44 байта

# id, instance, name_original[128], name_user[128]
SENSOR_FORMAT = "<II128s128s"
SENSOR_SIZE = struct.calcsize(SENSOR_FORMAT)  # 264 байта

# type(u32), sensor_index(u32), id(u32), name_original[128], name_user[128],
# unit[16], value(f64), value_min(f64), value_max(f64), value_avg(f64)
ENTRY_FORMAT = "<III128s128s16sdddd"
ENTRY_SIZE = struct.calcsize(ENTRY_FORMAT)  # 316 байт

SENSOR_TYPE_NAMES = {
    0: "None", 1: "Temperature", 2: "Voltage", 3: "Fan",
    4: "Current", 5: "Power", 6: "Clock", 7: "Usage", 8: "Other",
}
TYPE_TEMPERATURE = 1
TYPE_USAGE = 7

FILE_MAP_READ = 0x0004


class HWiNFOReader:
    """
    Низкоуровневый ридер Shared Memory HWiNFO. Каждый вызов get_entries()
    заново открывает область памяти -- так проще пережить ситуации, когда
    HWiNFO ещё не запущен, временно выключил SHM (12-часовой лимит
    free-версии) или был перезапущен между вызовами.
    """

    def __init__(self):
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._setup_signatures()
        self._last_error: Optional[str] = None

    def _setup_signatures(self) -> None:
        """
        Явно задаём argtypes/restype для функций WinAPI.

        Это критично на 64-битной Windows: без явного restype ctypes
        по умолчанию считает возвращаемое значение 32-битным int и
        ОБРЕЗАЕТ указатели (MapViewOfFile возвращает адрес -- 64-битный
        указатель). Без этой настройки код тихо читал бы память по
        неверному, обрезанному адресу -- ровно тот же класс багов
        ("тихо неверные данные вместо ошибки"), что мы уже несколько
        раз ловили в этом проекте.
        """
        k = self._kernel32
        k.OpenFileMappingW.restype = ctypes.wintypes.HANDLE
        k.OpenFileMappingW.argtypes = [
            ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.LPCWSTR
        ]
        k.MapViewOfFile.restype = ctypes.wintypes.LPVOID
        k.MapViewOfFile.argtypes = [
            ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD,
            ctypes.wintypes.DWORD, ctypes.c_size_t
        ]
        k.UnmapViewOfFile.restype = ctypes.wintypes.BOOL
        k.UnmapViewOfFile.argtypes = [ctypes.wintypes.LPCVOID]
        k.CloseHandle.restype = ctypes.wintypes.BOOL
        k.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]

    def _open_mapping(self):
        """Пробует оба варианта имени (Global\\ и без) по очереди."""
        for name in SHARED_MEM_NAMES:
            handle = self._kernel32.OpenFileMappingW(FILE_MAP_READ, False, name)
            if handle:
                addr = self._kernel32.MapViewOfFile(handle, FILE_MAP_READ, 0, 0, 0)
                if addr:
                    return handle, addr
                self._kernel32.CloseHandle(handle)
        return None, None

    def get_entries(self) -> List[Dict[str, Union[str, float]]]:
        """
        Возвращает список всех показаний в виде словарей:
            {sensor_name, type, label, unit, value}

        Пустой список означает: HWiNFO не запущен, Shared Memory Support
        выключена (в т.ч. истёк 12-часовой лимит free-версии) или ещё
        не успел опубликовать данные. Причину смотри в get_last_error().
        """
        handle, addr = self._open_mapping()
        if not handle:
            self._last_error = (
                "HWiNFO shared memory not found. Проверьте: 1) HWiNFO запущен, "
                "2) в его настройках включено Shared Memory Support, "
                "3) в бесплатной версии это могло отключиться через 12 часов -- "
                "включите галочку в HWiNFO заново."
            )
            return []

        try:
            header_bytes = ctypes.string_at(addr, HEADER_SIZE)
            (magic, version, version2, last_update,
             sensor_off, sensor_size, sensor_count,
             entry_off, entry_size, entry_count) = struct.unpack(HEADER_FORMAT, header_bytes)

            if magic != HEADER_MAGIC:
                self._last_error = f"Unexpected HWiNFO shared memory magic: {magic:#x}"
                return []

            # Группы-сенсоры
            sensor_names: Dict[int, str] = {}
            for i in range(sensor_count):
                off = sensor_off + i * sensor_size
                raw = ctypes.string_at(addr + off, SENSOR_SIZE)
                _sid, _inst, name_orig, name_user = struct.unpack(SENSOR_FORMAT, raw)
                sensor_names[i] = self._decode(name_user) or self._decode(name_orig)

            # Конкретные показания
            entries = []
            for i in range(entry_count):
                off = entry_off + i * entry_size
                raw = ctypes.string_at(addr + off, ENTRY_SIZE)
                (etype, sensor_index, _eid, name_orig, name_user,
                 unit, value, _vmin, _vmax, _vavg) = struct.unpack(ENTRY_FORMAT, raw)

                entries.append({
                    "sensor_name": sensor_names.get(sensor_index, "?"),
                    "type": SENSOR_TYPE_NAMES.get(etype, "Unknown"),
                    "type_id": etype,
                    "label": self._decode(name_user) or self._decode(name_orig),
                    "unit": self._decode(unit),
                    "value": value,
                })

            self._last_error = None
            return entries

        except Exception as e:
            self._last_error = f"Error reading HWiNFO shared memory: {e}"
            logger.error(self._last_error)
            return []

        finally:
            self._kernel32.UnmapViewOfFile(addr)
            self._kernel32.CloseHandle(handle)

    @staticmethod
    def _decode(raw_bytes: bytes) -> str:
        return raw_bytes.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()

    def get_last_error(self) -> Optional[str]:
        return self._last_error


# ----------------------------------------------------------------------
# Высокоуровневая обёртка -- ГИБРИДНАЯ схема сопоставления:
#
# 1) Сначала пробуем ТОЧНЫЕ строки под конкретную сборку (Ryzen 5 7500F +
#    Palit RTX 5070 + GIGABYTE B850) -- это быстро и стопроцентно надёжно
#    именно на этом ПК, так их подобрал и проверил сам пользователь по
#    реальному дампу diag_hwinfo.py.
# 2) Если точное совпадение не нашлось (сменили видеокарту/процессор,
#    запустили тот же код на другом ПК) -- откатываемся на эвристику по
#    подстрокам, как было в первой версии. Она грубее, но не привязана
#    к конкретной модели железа.
# ----------------------------------------------------------------------
class HWiNFOTelemetryReader:
    """
    Извлекает CPU temp / GPU temp / RAM usage из показаний HWiNFO.

    Использует гибридный подход:
    1. Сначала ищет точные совпадения для текущего железа (Ryzen 5 7500F, RTX 5070).
    2. Если точные сенсоры не найдены (например, после апгрейда),
       использует эвристический поиск по ключевым словам (fallback).
    """

    def __init__(self):
        self._reader = HWiNFOReader()
        self._cache: Dict[str, Union[int, float]] = {
            "cpu_temp": -1, "cpu_usage": -1, "gpu_temp": -1, "gpu_usage": -1, "ram_usage": -1, "fps": -1
        }
        self._cache_time: float = 0
        self._cache_ttl: float = 2.0

    def get_telemetry(self) -> Dict[str, Union[int, float]]:
        now = time.time()
        if (now - self._cache_time) < self._cache_ttl:
            return self._cache

        entries = self._reader.get_entries()

        if not entries:
            self._cache = {"cpu_temp": -1, "cpu_usage": -1, "gpu_temp": -1, "gpu_usage": -1, "ram_usage": -1, "fps": -1}
            self._cache_time = now
            return self._cache

        # 1. ПОПЫТКА №1: Точный поиск (Fast Path)
        cpu_temp, cpu_usage, gpu_temp, gpu_usage, ram_usage, fps = -1, -1, -1, -1, -1, -1

        for e in entries:
            sensor = e.get("sensor_name", "")
            label = e.get("label", "")
            val = e.get("value", -1)

            if sensor == "CPU [#0]: AMD Ryzen 5 7500F: Enhanced" and label == "CPU (Tctl/Tdie)":
                cpu_temp = val
            elif sensor == "CPU [#0]: AMD Ryzen 5 7500F: Enhanced" and label == "Total CPU Usage":
                cpu_usage = val
            elif sensor == "dGPU [#0]: NVIDIA GeForce RTX 5070: Palit GeForce RTX 5070 Infinity 3/White OC" and label == "GPU Temperature":
                gpu_temp = val
            elif sensor == "dGPU [#0]: NVIDIA GeForce RTX 5070: Palit GeForce RTX 5070 Infinity 3/White OC" and label == "GPU Core Load":
                gpu_usage = val
            elif sensor == "System: GIGABYTE B850 GAMING WIFI6" and label == "Physical Memory Load":
                ram_usage = val

        # 2. ПОПЫТКА №2: Эвристика, если точный поиск ничего не дал (Fallback)
        if fps <= 0:
            fps_fallback = self._pick_fps(entries)
            fps = fps_fallback if fps_fallback is not None else -1

        if cpu_temp <= 0:
            cpu_fallback = self._pick_cpu_temp(entries)
            cpu_temp = cpu_fallback if cpu_fallback is not None else -1

        if cpu_usage <= 0:
            cpu_u_fallback = self._pick_cpu_usage(entries)
            cpu_usage = cpu_u_fallback if cpu_u_fallback is not None else -1

        if gpu_temp <= 0:
            gpu_fallback = self._pick_gpu_temp(entries)
            gpu_temp = gpu_fallback if gpu_fallback is not None else -1

        if gpu_usage <= 0:
            gpu_u_fallback = self._pick_gpu_usage(entries)
            gpu_usage = gpu_u_fallback if gpu_u_fallback is not None else -1

        if ram_usage <= 0:
            ram_fallback = self._pick_ram_usage(entries)
            ram_usage = ram_fallback if ram_fallback is not None else -1

        self._cache = {
            "cpu_temp": cpu_temp if cpu_temp > 0 else -1,
            "cpu_usage": cpu_usage if cpu_usage > 0 else -1,
            "gpu_temp": gpu_temp if gpu_temp > 0 else -1,
            "gpu_usage": gpu_usage if gpu_usage > 0 else -1,
            "ram_usage": ram_usage if ram_usage > 0 else -1,
            "fps": fps if fps > 0 else -1,
        }
        self._cache_time = now
        return self._cache

    @staticmethod
    def _is_valid(value: Optional[float]) -> bool:
        return value is not None and value > 0

    def _pick_cpu_usage(self, entries: List[Dict]) -> Optional[float]:
        candidates = []
        for e in entries:
            # Usage might be type_id == 7 (Usage) or sometimes 8 (Other)
            if e.get("type_id") not in (7, 8):
                continue
            sensor_lower = e.get("sensor_name", "").lower()
            label_lower = e.get("label", "").lower()
            if "gpu" in sensor_lower or "nvidia" in sensor_lower or "radeon" in sensor_lower:
                continue
            if "cpu" not in sensor_lower:
                continue
            if not self._is_valid(e.get("value")):
                continue
            if "total" in label_lower and "usage" in label_lower:
                candidates.insert(0, e["value"]) # Priority
            elif "usage" in label_lower or "load" in label_lower:
                candidates.append(e["value"])
        if candidates: return candidates[0]
        return None

    def _pick_gpu_usage(self, entries: List[Dict]) -> Optional[float]:
        candidates = []
        for e in entries:
            if e.get("type_id") not in (7, 8):
                continue
            sensor_lower = e.get("sensor_name", "").lower()
            label_lower = e.get("label", "").lower()
            if not ("gpu" in sensor_lower or "nvidia" in sensor_lower or "radeon" in sensor_lower):
                continue
            if not self._is_valid(e.get("value")):
                continue
            if "core" in label_lower and ("load" in label_lower or "usage" in label_lower):
                candidates.insert(0, e["value"]) # Priority
            elif "load" in label_lower or "usage" in label_lower:
                candidates.append(e["value"])
        if candidates: return candidates[0]
        return None

    def _pick_cpu_temp(self, entries: List[Dict]) -> Optional[float]:
        candidates_priority = []
        candidates_fallback = []
        for e in entries:
            if e.get("type_id") != 1:  # TYPE_TEMPERATURE
                continue
            sensor_lower = e.get("sensor_name", "").lower()
            label_lower = e.get("label", "").lower()
            if "gpu" in sensor_lower or "nvidia" in sensor_lower or "radeon" in sensor_lower:
                continue
            if "cpu" not in sensor_lower:
                continue
            if not self._is_valid(e.get("value")):
                continue
            if "package" in label_lower or "tctl" in label_lower or "tdie" in label_lower:
                candidates_priority.append(e["value"])
            else:
                candidates_fallback.append(e["value"])
        if candidates_priority: return candidates_priority[0]
        if candidates_fallback: return candidates_fallback[0]
        return None

    def _pick_gpu_temp(self, entries: List[Dict]) -> Optional[float]:
        candidates_priority = []
        candidates_fallback = []
        for e in entries:
            if e.get("type_id") != 1:  # TYPE_TEMPERATURE
                continue
            sensor_lower = e.get("sensor_name", "").lower()
            label_lower = e.get("label", "").lower()
            if not ("gpu" in sensor_lower or "nvidia" in sensor_lower or "radeon" in sensor_lower):
                continue
            if not self._is_valid(e.get("value")):
                continue
            if "hot spot" in label_lower or "junction" in label_lower:
                continue
            if "gpu core" in label_lower or label_lower == "gpu temperature":
                candidates_priority.append(e["value"])
            else:
                candidates_fallback.append(e["value"])
        if candidates_priority: return candidates_priority[0]
        if candidates_fallback: return candidates_fallback[0]
        return None

    def _pick_fps(self, entries: List[Dict]) -> Optional[float]:
        candidates_exact = []
        candidates_fallback = []

        for e in entries:
            sensor_lower = e.get("sensor_name", "").lower()
            label_lower = e.get("label", "").lower()

            # RTSS usually exposes "Framerate" under "RTSS" sensor.
            if "fps" in label_lower or "framerate" in label_lower or "frame rate" in label_lower:
                if not self._is_valid(e.get("value")):
                    continue

                # Exclude min/max/avg/1% low metrics
                if any(x in label_lower for x in ["max", "min", "avg", "average", "low", "1%", "0.1%"]):
                    continue

                # Prefer exact match
                if label_lower in ["fps", "framerate", "frame rate"]:
                    candidates_exact.append((sensor_lower, e["value"]))
                else:
                    candidates_fallback.append((sensor_lower, e["value"]))

        # Prioritize RTSS sensors among exact matches
        for sensor, val in candidates_exact:
            if "rtss" in sensor:
                return val
        if candidates_exact: return candidates_exact[0][1]

        # Prioritize RTSS sensors among fallback matches
        for sensor, val in candidates_fallback:
            if "rtss" in sensor:
                return val
        if candidates_fallback: return candidates_fallback[0][1]

        return None

    def _pick_ram_usage(self, entries: List[Dict]) -> Optional[float]:
        for e in entries:
            # ВАЖНО: НЕ фильтруем по type_id здесь. На разных системах/версиях
            # HWiNFO классифицирует "Physical Memory Load" по-разному -- где-то
            # это Usage(7), а по реальному дампу пользователя (GIGABYTE H510M)
            # это оказался Other(8). Жёсткий фильтр по type_id==7 на такой
            # раскладке молча отбрасывал нужную запись ещё до проверки текста
            # лейбла -- вот и был баг. Полагаемся только на текст лейбла и
            # единицу измерения (%), этого достаточно и надёжнее.
            sensor_lower = e.get("sensor_name", "").lower()
            label_lower = e.get("label", "").lower()
            unit = e.get("unit", "").strip()

            if "gpu" in sensor_lower or "nvidia" in sensor_lower or "radeon" in sensor_lower:
                continue  # видеопамять — не то, что нужно (см. историю с "2% вместо 56%")
            if "physical memory" not in label_lower:
                continue  # тем же приёмом отсекаем "Virtual Memory Load"
            if "load" not in label_lower:
                continue  # отсекаем "Physical Memory Used/Available" (это МБ, не %)
            if "%" not in unit:
                continue  # доп. страховка от абсолютных значений в МБ
            if self._is_valid(e.get("value")):
                return e["value"]
        return None

    def get_last_error(self) -> Optional[str]:
        return self._reader.get_last_error()
