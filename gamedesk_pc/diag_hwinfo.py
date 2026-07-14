"""
diag_hwinfo.py -- дамп всех показаний HWiNFO из Shared Memory.

Перед запуском:
1. Запусти HWiNFO (можно в режиме Sensors only).
2. В настройках HWiNFO включи Shared Memory Support
   (правый клик по иконке в трее -> Settings -> General).
3. Не закрывай окно Sensors HWiNFO (можно свернуть).

Запуск: python diag_hwinfo.py

Если видишь "HWiNFO shared memory not found" -- проверь три пункта выше.
Если структуры распознаются, но конкретный нужный сенсор (например CPU
Package) не подхватывается в GameDesk -- пришли ПОЛНЫЙ вывод этого
скрипта, по нему можно точно подправить сопоставление лейблов.
"""

from hwinfo_reader import HWiNFOReader

reader = HWiNFOReader()
entries = reader.get_entries()

if not entries:
    print("Ничего не найдено.")
    print("Причина:", reader.get_last_error())
else:
    print(f"Всего показаний: {len(entries)}\n")
    current_sensor = None
    for e in entries:
        if e["sensor_name"] != current_sensor:
            current_sensor = e["sensor_name"]
            print(f"\n[{current_sensor}]")
        print(f"    {e['type']:<12} | {e['label']:<40} = {e['value']} {e['unit']}")
