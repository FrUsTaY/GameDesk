# 🤖 GameDesk — Промты для Deepseek и GigaCode по дням

> **Как пользоваться этим файлом:**
> - Блоки `### 🟦 DEEPSEEK` — копируй и вставляй в чат Deepseek целиком
> - Блоки `### 🟩 GIGACODE` — команды для GigaCode прямо в VS Code
> - Блоки `### 📌 ТЕБЕ` — пометки и действия которые нужно сделать руками
> - Перед каждой сессией с Deepseek сначала кидай ему ТЗ и Roadmap, затем промт из этого файла
> - Не меняй промты — они составлены точно под ТЗ и Roadmap v2.3

---

## ═══════════════════════════════════
## PHASE 0-1 — Среда + Hardware Bring-Up
## ═══════════════════════════════════

---

### ДЕНЬ 1 — Установка среды, первый запуск дисплея

---

### 📌 ТЕБЕ
1. Скачай и установи Arduino IDE 2.x с официального сайта arduino.cc
2. В Arduino IDE: File → Preferences → Additional boards manager URLs добавь:
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
3. Tools → Board → Boards Manager → найди "esp32 by Espressif" → Install
4. Tools → Manage Libraries → установи:
   - TFT_eSPI by Bodmer
5. Подключи ESP32 по USB. Если не определяется — установи драйвер CH340 или CP2102 (смотри на чипе возле USB-разъёма платы ESP32)
6. Tools → Board → выбери "ESP32 Dev Module"
7. Tools → Port → выбери свой COM-порт

---

### 🟦 DEEPSEEK — Промт 1.1: Конфиг TFT_eSPI под ST7789V

Я разрабатываю проект GameDesk на NodeMCU ESP-32S (38 pin).
Дисплей: TFT LCD 2.8", контроллер ST7789V, разрешение 320x240, интерфейс SPI, альбомная ориентация.
Тачскрин на плате НЕ распаян (посадочное место U1 пустое). Управление — 5 тактовых кнопок.
Библиотека дисплея: TFT_eSPI by Bodmer (последняя версия).

Задача: сгенерируй корректный файл User_Setup.h для библиотеки TFT_eSPI под этот дисплей.
Используй стандартные SPI-пины ESP32 (VSPI: MOSI=23, MISO=19, SCK=18).
CS дисплея на GPIO 15, DC на GPIO 2, RST на GPIO 4, LED (подсветка) на GPIO 21.
Питание дисплея: VCC → 5V ESP32 (на плате есть стабилизатор LDO, он сам делает 3.3V для чипа).
Ориентация: landscape (320x240), цвета 65K RGB565.
Не включай никаких лишних опций — только то что нужно для данного дисплея.
Добавь комментарии на русском языке к каждой важной строке.

---

### 📌 ТЕБЕ после получения User_Setup.h
- Файл User_Setup.h нужно положить в папку библиотеки TFT_eSPI, заменив существующий.
- Путь обычно: Documents/Arduino/libraries/TFT_eSPI/User_Setup.h
- Пины (CS=15, DC=2, RST=4, LED=21) — это стандарт.
- VCC дисплея → пин 5V на ESP32 (не 3V3! на плате стоит стабилизатор LDO).

---

### 🟦 DEEPSEEK — Промт 1.2: Hello GameDesk

Проект GameDesk, NodeMCU ESP-32S, дисплей ST7789V 320x240, библиотека TFT_eSPI.
User_Setup.h уже настроен (CS=15, DC=2, RST=4, LED=21, SPI VSPI).

Напиши скетч Arduino (.ino) который:
1. Инициализирует дисплей в альбомной ориентации (320x240)
2. Заливает фон тёмно-синим цветом
3. Выводит по центру экрана белый текст "HELLO GAMEDECK" шрифтом 3 (TFT_eSPI font)
4. Под надписью выводит жёлтым цветом текст "320x240 ST7789V"
5. В Serial Monitor (115200 baud) выводит "Display OK" после успешной инициализации

Код должен быть чистым, с комментариями на русском языке.

---

### 📌 ТЕБЕ после заливки скетча
- Если экран остался белым или чёрным — скорее всего пины не совпадают. Проверь физическое подключение.
- Если цвета перепутаны (синее выглядит красным) — в User_Setup.h попробуй раскомментировать #define TFT_RGB_ORDER TFT_BGR
- Если всё ок — сфоткай, это первая победа!

---

### ДЕНЬ 2 — Подключение кнопок, тест

---

### 🟦 DEEPSEEK — Промт 2.1: Тест всех 5 кнопок

Проект GameDesk, NodeMCU ESP-32S.
Управление: 5 тактовых кнопок (INPUT_PULLUP, нажатие = LOW).
Пины: LEFT=GPIO26, RIGHT=GPIO27, UP=GPIO14, DOWN=GPIO32, CENTER=GPIO13.

Напиши скетч Arduino который:
1. Инициализирует все 5 пинов как INPUT_PULLUP
2. В loop() — при нажатии любой кнопки выводит в Serial Monitor её название: "Button: LEFT" и т.д.
3. Программный антидребезг: 40 мс через millis() (не delay())
4. Кнопка нажата когда пин LOW

Комментарии на русском языке.

---

### 📌 ТЕБЕ — Проверка кнопок
Нажми каждую из 5 кнопок и убедись что в Serial Monitor появляется её название.
Если кнопка "дрожит" (несколько срабатываний за одно нажатие) — увеличь фильтр с 40 до 60 мс в config.h.

---

### 🟦 DEEPSEEK — Промт 2.2: Короткое и долгое нажатие CENTER

Проект GameDesk, NodeMCU ESP-32S (38 pin), дисплей ST7789V 320x240.
Кнопка CENTER на GPIO13, INPUT_PULLUP.

Напиши скетч Arduino реализующий определение типа нажатия CENTER:
- короткое: кнопка отпущена раньше 500 мс → вывести "CENTER: SHORT"
- долгое: кнопка удерживается >= 1500 мс → вывести "CENTER: LONG"

Требования:
- non-blocking (millis(), никаких delay())
- долгое нажатие НЕ вызывает короткое
- антидребезг 40 мс при нажатии и отпускании

Комментарии на русском языке.

---

### 📌 ТЕБЕ после теста
- Нажми CENTER коротко (<0.5 с) → Serial должен показать "CENTER: SHORT"
- Нажми CENTER долго (2 сек) → Serial должен показать "CENTER: LONG" — и НЕ должен показать "CENTER: SHORT" после
- Если оба срабатывают одновременно — скажи Deepseek что long вызывает short, попроси исправить порядок проверки
- Если кнопка дребезжит (несколько срабатываний) — увеличь фильтр с 40 до 60 мс в config.h

---

## ═══════════════════════════════════
## PHASE 2 — ESP32 UI Foundation
## ═══════════════════════════════════

---

### ДЕНЬ 3 — State Machine + экраны-заглушки

---

### 🟩 GIGACODE — Создай структуру проекта ESP32

Создай структуру папок и файлов для Arduino-проекта GameDesk_ESP32:

GameDesk_ESP32/
├── GameDesk_ESP32.ino     (главный файл, setup + loop)
├── config.h               (все константы: пины кнопок, цвета, таймауты)
├── state_machine.h/.cpp   (enum состояний + логика переходов)
├── display_manager.h/.cpp (отрисовка экранов)
├── button_handler.h/.cpp  (обработка 5 кнопок, антидребезг)
└── serial_handler.h/.cpp  (приём и парсинг пакетов — пока заглушка)

В каждом файле создай базовую структуру с include guards и пустыми функциями.
Добавь комментарии на русском языке о назначении каждого файла.

---

### 🟦 DEEPSEEK — Промт 3.1: config.h

Проект GameDesk для NodeMCU ESP-32S.
Дисплей: ST7789V 320x240. Тачскрин не распаян — управление кнопками.

Создай файл config.h со всеми константами проекта:

// Пины кнопок
#define BTN_LEFT    26
#define BTN_RIGHT   27
#define BTN_UP      14
#define BTN_DOWN    32
#define BTN_CENTER  13

// Таймауты кнопок (миллисекунды)
#define BTN_DEBOUNCE_MS   40    // антидребезг
#define BTN_SHORT_MAX_MS 500    // максимум для короткого нажатия
#define BTN_LONG_MS     1500    // минимум для долгого нажатия

// Питание дисплея
// VCC дисплея → 5V ESP32 (на плате LDO стабилизатор U2)

// Таймауты Serial
#define OFFLINE_TIMEOUT  5000

// Протокол
#define SERIAL_BAUD     115200
#define PACKET_BUFFER    1024

Также добавь цвета RGB565 для тёмной темы: фон, текст, акцент (жёлтый), CPU (оранжевый), GPU (зелёный), RAM (синий), OFFLINE (красный), выделение (тёмно-синий фон), разделители (тёмно-серый).
Комментарии на русском языке к каждой группе констант.

---

### 🟦 DEEPSEEK — Промт 3.2: State Machine

Проект GameDesk, ESP32, файл state_machine.h/.cpp.

Реализуй state machine для UI устройства.

Состояния (enum UIState):
  BOOT, HOME, MONITOR, STATS, RECENT_GAMES, DETAIL_VIEW, SETTINGS, OFFLINE

Правила переходов согласно ТЗ:
- LEFT/RIGHT: кольцевое переключение HOME → MONITOR → STATS → RECENT_GAMES → HOME
- CENTER долгое (≥1500 мс) из любого состояния кроме BOOT: вход в SETTINGS / выход из SETTINGS
- CENTER короткое в RECENT_GAMES: переход в DETAIL_VIEW
- LEFT в DETAIL_VIEW: возврат в RECENT_GAMES (LEFT не переключает экран в этом состоянии)
- В состоянии SETTINGS: LEFT и RIGHT ЗАБЛОКИРОВАНЫ, работают только UP/DOWN/CENTER
- потеря Serial > 5 секунд: переход в OFFLINE (принудительно, запомнить lastActiveState)
- восстановление Serial: возврат на lastActiveState
- в состоянии OFFLINE навигация заблокирована

Реализуй:
- void setState(UIState newState)
- UIState getState()
- UIState getLastActiveState()
- void onLeft(), void onRight(), void onUp(), void onDown()
- void onCenterShort(), void onCenterLong()
- void onSerialLost(), void onSerialRestored()

lastActiveState сохраняется при любом переходе кроме OFFLINE и SETTINGS.
При каждой смене состояния выводи в Serial: "[STATE] → HOME" (или другое состояние).
Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 3.3: Заглушки всех экранов

Проект GameDesk, ESP32, дисплей ST7789V 320x240, библиотека TFT_eSPI.
Файл display_manager.h/.cpp.

Реализуй отрисовку заглушек для всех экранов.
Каждый экран: заливает фон тёмным цветом, выводит название экрана вверху белым шрифтом 2, выводит мок-данные по центру жёлтым шрифтом 4.

Экраны и мок-данные:
- HOME: вверху "HOME", центр — "RDR2" крупно и "01:23:45" под ним
- MONITOR: вверху "MONITOR", центр — "CPU: 72C / GPU: 68C / RAM: 41%"
- STATS: вверху "STATS", центр — "Week: 14:32 / Month: 42:11 / Games: 8"
- RECENT_GAMES: вверху "RECENT GAMES", список из 3 строк: "RDR2", "CS2", "CIV6"
- DETAIL_VIEW: вверху "DETAIL VIEW", данные по игре RDR2
- SETTINGS: вверху "SETTINGS", три пункта: "Connection Status", "Restart Device", "About"
- OFFLINE: чёрный фон, красным по центру "PC OFFLINE", серым под ним "Нет соединения"

Функции:
- void drawScreen(UIState state) — главный диспетчер
- void drawHome(), drawMonitor(), drawStats(), drawRecentGames(), drawDetailView(), drawSettings(), drawOffline()

Запрещено fillScreen() при каждом обновлении данных — только при смене экрана.
Комментарии на русском языке.

---

### ДЕНЬ 4 — Button Handler + интеграция в loop

---

### 🟦 DEEPSEEK — Промт 4.1: Button Handler (полный)

Проект GameDesk, NodeMCU ESP-32S (38 pin). Файл button_handler.h/.cpp.

Реализуй полный неблокирующий обработчик 5 кнопок.

Пины (из config.h): BTN_LEFT=26, BTN_RIGHT=27, BTN_UP=14, BTN_DOWN=32, BTN_CENTER=13.
Все кнопки: INPUT_PULLUP, нажатие = LOW.

Требования из ТЗ §9:
- антидребезг: фильтр BTN_DEBOUNCE_MS (40 мс) через millis()
- CENTER короткое: отпущена раньше BTN_SHORT_MAX_MS (500 мс) → ButtonEvent::CENTER_SHORT
- CENTER долгое: удерживается ≥ BTN_LONG_MS (1500 мс) → ButtonEvent::CENTER_LONG
- ВАЖНО: CENTER долгое НЕ должно вызывать CENTER короткое
- LEFT/RIGHT/UP/DOWN: срабатывают при нажатии (после антидребезга)

enum ButtonEvent { NONE, LEFT, RIGHT, UP, DOWN, CENTER_SHORT, CENTER_LONG };

Главная функция: ButtonEvent processButtons()
Вызывается в каждой итерации loop(), non-blocking, использует millis().
Возвращает одно событие за вызов (не накапливает очередь).

Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 4.2: Главный loop — интеграция всех модулей

Проект GameDesk, ESP32. Файл GameDesk_ESP32.ino.

Напиши главный файл проекта который объединяет все модули:

setup():
- Serial.begin(115200)
- Инициализация дисплея (TFT_eSPI)
- Инициализация кнопок (pinMode INPUT_PULLUP для всех 5)
- setState(BOOT)
- Запустить BOOT-последовательность (пока заглушка: пауза 1 сек → setState(HOME))

loop():
1. ButtonEvent btn = processButtons()
2. Передать событие в state machine: if(btn == LEFT) onLeft(); if(btn == CENTER_LONG) onCenterLong(); и т.д.
3. Если состояние изменилось — drawScreen(getState())
4. Вызвать handleSerial() (заглушка пока)

Смена экрана только при реальном изменении состояния — не перерисовывать каждый кадр.
Никаких delay() в loop().
Комментарии на русском языке.

---

### 📌 ТЕБЕ — Тест после Дня 4
Залей прошивку. Проверь руками:
- [ ] LEFT/RIGHT переключают экраны по кольцу (HOME → MONITOR → STATS → RECENT GAMES → HOME)
- [ ] CENTER долгое (2 сек) → входит в SETTINGS
- [ ] CENTER долгое ещё раз → выходит из SETTINGS
- [ ] В Serial Monitor видны переходы: [STATE] → HOME и т.д.
- [ ] CENTER короткое в RECENT GAMES → DETAIL VIEW
- [ ] LEFT в DETAIL VIEW → обратно в RECENT GAMES

---

### ДЕНЬ 5 — BOOT-экран + DEBUG MODE + SETTINGS

---

### 🟦 DEEPSEEK — Промт 5.1: BOOT-анимация с DEBUG MODE

Проект GameDesk, ESP32, дисплей ST7789V 320x240, библиотека TFT_eSPI.

Реализуй BOOT-последовательность (в display_manager.cpp + главный файл):

1. Чёрный фон
2. Логотип: текст "GAME" крупным шрифтом (font 6) по центру, под ним "DESK" — имитация fade-in через 5 шагов от тёмно-серого к белому
3. Progress bar внизу: полоса 280x8 пикселей, белая рамка, заполняется синим от 0% до 100% за 3 секунды, шаг каждые 100 мс
4. Общее время BOOT <= 4 секунд
5. После окончания → setState(HOME)

Параллельно с анимацией: опрашивать кнопку CENTER каждые 50 мс (для DEBUG MODE).
DEBUG MODE: если в первые 2 секунды анимации удерживается кнопка CENTER (BTN_CENTER LOW) — установить флаг bool debugMode = true и вывести в Serial "=== DEBUG MODE ACTIVATED ===".
Если debugMode=true, все последующие события выводить в Serial с префиксом [DBG].

Всё через millis(), никаких delay().
Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 5.2: Экран SETTINGS (полноценный)

Проект GameDesk, ESP32, дисплей ST7789V 320x240.

Реализуй полноценный экран SETTINGS в display_manager.cpp.

Пункты меню строго по ТЗ v1.0:
1. Connection Status — показывает статус (Connected/Offline), VER=1, время последнего пакета ("5 sec ago"), аптайм устройства
2. Restart Device — подтверждение "Перезагрузить? [Да] / [Нет]", CENTER = да (ESP.restart()), LEFT/RIGHT = нет
3. About — "FW: 1.0 / Device: ESP32-32S NodeMCU / Display: ST7789V", CENTER/LEFT = назад
4. Exit — выход из SETTINGS (то же что CENTER долгое)

Навигация:
- UP/DOWN — перемещение между пунктами (активный подсвечивается синим фоном)
- CENTER короткое — выбрать пункт / подтвердить
- CENTER долгое — выйти из SETTINGS

Для Connection Status нужна структура ConnectionStatus {bool connected; int ver; unsigned long lastPacketMs;} которую заполняет serial_handler.
Комментарии на русском языке.

---

### ДЕНЬ 6 — Буфер Phase 2

---

### 📌 ТЕБЕ — Чеклист Phase 2 (пройди руками)
- [ ] Все 7 экранов отображаются без артефактов и мерцания
- [ ] Все кнопки работают согласно ТЗ §4 и §9
- [ ] BOOT <= 4 секунды, логотип и progress bar видны
- [ ] DEBUG MODE активируется удержанием CENTER при загрузке → Serial показывает лог
- [ ] SETTINGS: все 4 пункта работают, Restart Device перезагружает ESP32
- [ ] В Serial Monitor видны переходы состояний при каждом жесте
- [ ] Нет залипаний и непредсказуемых переходов

Если что-то не работает — используй промт 6.1 ниже.

---

### 🟦 DEEPSEEK — Промт 6.1: Исправление бага (шаблон)

Проект GameDesk, ESP32 (ST7789V 320x240, кнопки LEFT/RIGHT/UP/DOWN/CENTER).

Проблема: [ОПИШИ ЧТО ИМЕННО ПРОИСХОДИТ И ЧТО ДОЛЖНО ПРОИСХОДИТЬ]

Шаги воспроизведения: [ОПИШИ]

Код файла [НАЗВАНИЕ]:
[ВСТАВЬ КОД]

Контекст: state machine (BOOT/HOME/MONITOR/STATS/RECENT_GAMES/DETAIL_VIEW/SETTINGS/OFFLINE), кнопки LEFT/RIGHT/UP/DOWN/CENTER (короткое/долгое), буфер Serial 1024 байт, парсинг после '>'.
Найди и исправь. Объясни причину на русском языке.

---

## ═══════════════════════════════════
## PHASE 3 — GameDesk Core (Python)
## ═══════════════════════════════════

---

### ДЕНЬ 7 — Python: структура проекта + процессы + статистика

---

### 🟩 GIGACODE — Создай структуру Python-проекта

Создай структуру Python-проекта gamedesk_pc:

gamedesk_pc/
├── main.py                 (точка входа, главный цикл)
├── process_monitor.py      (мониторинг процессов через psutil)
├── session_tracker.py      (учёт времени игровых сессий)
├── stats_manager.py        (чтение/запись games.json)
├── serial_sender.py        (отправка пакетов — заглушка пока)
├── packet_builder.py       (формирование строк пакетов)
├── telemetry.py            (CPU/GPU/RAM — заглушка пока)
├── config.py               (настройки: список игр, пути, таймауты)
├── games.json              (пустой шаблон)
└── requirements.txt        (psutil, pyserial, pythonnet)

В каждом .py файле создай базовую структуру с docstring и пустыми функциями.

---

### 🟦 DEEPSEEK — Промт 7.1: config.py + шаблон games.json

Проект GameDesk, Python. Создай файл config.py.

Содержимое:
- Словарь GAMES: имя процесса (например "RDR2.exe") → отображаемое название ("RDR2"). Добавь 15 популярных игр с правильными именами .exe процессов (RDR2, CS2, Cyberpunk 2077, Witcher 3, GTA5, Elden Ring, Valorant, Apex Legends, Fortnite, Minecraft, Dota 2, Path of Exile 2, Baldur's Gate 3, Civilization 6, FIFA/EA FC)
- Настройки Serial: SERIAL_BAUD=115200, SERIAL_TIMEOUT=1.0, PING_TIMEOUT=1.0
- Частота отправки: SEND_RATE_HZ=1, MAX_RATE_HZ=10
- Пути: STATS_FILE="games.json", LOG_FILE="gamedesk.log"
- Таймауты: OFFLINE_TIMEOUT=5 (сек), LIST_SEND_INTERVAL=30 (сек)
- Сброс статистики: WEEKLY_RESET_DAY=0 (понедельник), MONTHLY_RESET_DAY=1

Также создай шаблон games.json со структурой:
{"games": {}, "meta": {"last_weekly_reset": "2025-01-01", "last_monthly_reset": "2025-01-01"}}
Где каждая запись игры: {"total_time": 0, "weekly_time": 0, "monthly_time": 0, "last_played": null, "session_count": 0}
Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 7.2: process_monitor.py + session_tracker.py

Проект GameDesk, Python. Зависимость: psutil.

process_monitor.py — класс ProcessMonitor:
- get_active_game() → str | None — проверяет запущенные процессы через psutil.process_iter(['name']), сравнивает с GAMES из config.py без учёта регистра, возвращает отображаемое название или None
- Если запущено несколько игр из списка — возвращать первую найденную

session_tracker.py — класс SessionTracker:
- start_session(game_name: str) — фиксирует время начала через time.time()
- end_session() → int — возвращает длительность в секундах, сбрасывает сессию
- get_session_duration() → int — текущая длительность в секундах
- get_session_str() → str — строка "HH:MM:SS"
- is_active() → bool

ВАЖНО: время сессии считает ТОЛЬКО Python. ESP32 только отображает строку.
Консольный вывод: "[RDR2] Session started", "[RDR2] Session ended: 01:23:45"
Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 7.3: stats_manager.py

Проект GameDesk, Python. Файл stats_manager.py.

Класс StatsManager:
- load() — загрузить из games.json, создать если не существует, вызвать проверки сброса
- save() — сохранить в games.json
- update_session(game_name, duration_seconds) — обновить total_time, weekly_time, monthly_time, last_played (ISO 8601), session_count; добавить игру если её нет
- check_and_reset_weekly() — если сегодня понедельник и ещё не сбрасывали на этой неделе → обнулить weekly_time всех игр, обновить meta
- check_and_reset_monthly() — если сегодня 1-е число и ещё не сбрасывали в этом месяце → обнулить monthly_time всех игр
- get_recent_games(limit=10) → list[dict] — список игр отсортированных по last_played (свежие сверху), максимум limit записей
- get_stats_summary() → dict с ключами: weekly_total_sec, monthly_total_sec, total_games

Если games.json повреждён — создать заново с пустой структурой.
Комментарии на русском языке.

---

### ДЕНЬ 8 — Packet builder + Dummy mode

---

### 🟦 DEEPSEEK — Промт 8.1: packet_builder.py

Проект GameDesk, Python. Файл packet_builder.py.

Класс PacketBuilder — формирует пакеты строго по протоколу из ТЗ.

Методы:

build_data_packet(game, session_str, state, fps, cpu, gpu, ram) → str
- state: "RUNNING" | "IDLE" | "OFFLINE"
- fps, cpu, gpu, ram: число или -1
- Пример: <VER=1;DEVICE=GAMEDECK;GAME=RDR2;SESSION=01:42:18;STATE=RUNNING;FPS=-1;CPU=54;GPU=67;RAM=41>
- VER и DEVICE добавлять в каждый 5-й пакет (счётчик внутри класса), в остальных опускать
- Максимальная длина пакета: 256 байт (если превышает — обрезать имя игры)

build_heartbeat() → str
- Возвращает: <STATE=IDLE;HB=1>

build_ping() → str
- Возвращает: <CMD=PING>

build_list_packet(games: list[dict]) → str
- games: список dict с ключами name, total_sec, last_played, weekly_sec, monthly_sec
- Формат в пакете: TOTAL="HH:MM" (без секунд), LAST="YYYY-MM-DD", WEEK="HH:MM", MONTH="HH:MM"
- Максимум 10 игр, максимальная длина всего LIST: 512 байт
- Пример вывода:
  <LIST=RECENT;COUNT=3>
  <GAME=RDR2;TOTAL=10:23;LAST=2025-03-15;WEEK=02:15;MONTH=08:42>
  </LIST>

Валидация имён: символы ; < > = заменять на пробел.
Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 8.2: Dummy mode + main.py основа

Проект GameDesk, Python. Файл main.py.

Реализуй два режима запуска:

Режим --dummy (для тестов без реального ESP32):
- Симулирует игру "RDR2" с растущим таймером
- Каждую секунду генерирует пакет через PacketBuilder и выводит в консоль с timestamp
- CPU/GPU/RAM случайны в диапазоне (50-80 / 45-75 / 35-55), FPS=-1
- Каждые 15 секунд — выводит LIST-пакет с 3 тестовыми играми
- Через 30 сек — смена игры на "CS2"
- Через 60 сек — завершение игры (STATE=IDLE, GAME=NONE)

Нормальный режим (заглушка пока):
- Загрузить StatsManager
- Вывести "GameDesk PC starting... Looking for ESP32"
- Бесконечный цикл с задержкой 1 сек (потом заменим на реальную логику)

Запуск: python main.py --dummy для тест-режима.
Комментарии на русском языке.

---

## ═══════════════════════════════════
## PHASE 4 — Serial + Protocol Core ⭐ KEY MILESTONE
## ═══════════════════════════════════

---

### ДЕНЬ 9 — Serial с обеих сторон

---

### 🟦 DEEPSEEK — Промт 9.1: serial_sender.py

Проект GameDesk, Python. Файл serial_sender.py. Зависимость: pyserial.

Класс SerialSender:

find_device() → str | None
- Перебирает все COM-порты через serial.tools.list_ports.comports()
- На каждый порт: открыть 115200 baud, отправить "<CMD=PING>\n", ждать ответ 1 секунду
- Если получен "<CMD=PONG;DEVICE=GAMEDECK;VER=1>" — вернуть имя порта
- ЗАПРЕЩЕНО хардкодить COM-порт
- При ошибке на порте — перейти к следующему, не падать

connect(port) → bool — открыть соединение
send(packet: str) → bool — отправить пакет + "\n", не чаще MAX_RATE_HZ раз/сек
disconnect()
is_connected() → bool

При send() выбросил исключение — установить is_connected=False, вернуть False, не крашить.
Консольный вывод с префиксом [SERIAL]: найден порт, подключение, разрыв, ошибки.
Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 9.2: serial_handler.cpp для ESP32

Проект GameDesk, ESP32. Файл serial_handler.h/.cpp.

Реализуй приём и парсинг пакетов по протоколу GameDesk.

Требования из ТЗ:
- Буфер char rxBuffer[1024]
- Парсинг ТОЛЬКО после получения символа '>' (полный пакет)
- Валидация: начинается с '<', заканчивается '>'
- Максимальная длина одиночного пакета: 256 байт — при превышении очистить буфер
- Максимальная длина LIST-пакета: 512 байт

Поддерживаемые пакеты:
1. DATA: <VER=1;DEVICE=GAMEDECK;GAME=...;SESSION=...;STATE=...;FPS=...;CPU=...;GPU=...;RAM=...>
2. Heartbeat: <STATE=IDLE;HB=1>
3. PING: <CMD=PING> → немедленно ответить <CMD=PONG;DEVICE=GAMEDECK;VER=1>
4. LIST: <LIST=RECENT;COUNT=N> ... <GAME=...> ... </LIST>
   - Буферизировать до </LIST>
   - Таймаут: если </LIST> не получен через 500 мс — выбросить буфер
   - Частичный LIST никогда не применять к UI

Структура ParsedData (глобальная, обновляется при каждом валидном пакете):
char game[32], session[10], state[10];
int fps, cpu, gpu, ram;
bool hasNewData;

Структура GameEntry[10] gameList — обновляется только при получении полного LIST.

Отслеживание offline: если прошло > OFFLINE_TIMEOUT мс без валидного пакета → вызвать state_machine.onSerialLost().
При получении пакета → вызвать state_machine.onSerialRestored().

В DEBUG MODE (если debugMode==true): выводить в Serial каждый пакет и результат парсинга.
Комментарии на русском языке.

---

### ДЕНЬ 10 — Первый сквозной тест + OFFLINE

---

### 📌 ТЕБЕ — Первый реальный запуск пайплайна
1. Запусти: python main.py --dummy → убедись что пакеты идут в консоль
2. Найди ESP32: добавь в main.py временно вызов serial_sender.find_device() и выведи найденный порт
3. Закрой Serial Monitor в Arduino IDE (один порт — одно подключение!)
4. Запусти нормальный режим с реальной отправкой
5. Смотри на дисплей ESP32 — данные должны появиться на экране MONITOR

---

### 🟦 DEEPSEEK — Промт 10.1: Финальный main.py (нормальный режим)

Проект GameDesk, Python. Финальная версия нормального режима в main.py.

Главный цикл:
1. stats_manager.load()
2. Искать ESP32 через serial_sender.find_device() — повторять каждые 5 сек если не найден, выводить "[SERIAL] Searching for GameDesk device..."
3. После подключения:
   a. process_monitor.get_active_game() — раз в секунду
   b. Если игра изменилась: end_session → update_session → save → start_session
   c. Строить пакет через packet_builder.build_data_packet()
   d. serial_sender.send(packet)
   e. Если нет активной игры: serial_sender.send(packet_builder.build_heartbeat())
   f. Каждые 30 сек: отправить LIST-пакет из stats_manager.get_recent_games()
   g. Если serial_sender потерял соединение: снова find_device()
4. Консольный статус каждые 5 сек: "Active: RDR2 | Session: 00:05:12 | CPU: 54C | GPU: 68C | RAM: 41%"
5. Ctrl+C: завершить сессию, сохранить stats, вывести "GameDesk stopped."

Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 10.2: OFFLINE-логика на ESP32

Проект GameDesk, ESP32. Доработка state_machine.cpp и display_manager.cpp.

Реализуй полную логику OFFLINE строго по ТЗ:

onSerialLost():
- lastActiveState = currentState (если не OFFLINE и не SETTINGS)
- setState(OFFLINE) — перейти в отдельное состояние OFFLINE
- Установить флаг isOffline = true
- Вызвать drawOffline() — экран с полностью чёрным фоном и красной надписью "PC OFFLINE" по центру (этот экран уже реализован в Промте 3.3)
- Заблокировать LEFT/RIGHT/UP/DOWN (навигация). CENTER долгое — оставить рабочим (доступ в SETTINGS даже в оффлайн)

onSerialRestored():
- isOffline = false
- setState(lastActiveState) — восстановить предыдущий экран (home, monitor, stats, recent games или detail view)
- Вывести в Serial: "[INFO] Connection restored → [STATE]"

Heartbeat <STATE=IDLE;HB=1> считается валидным пакетом (сбрасывает таймер offline).

Важно: не рисовать поверх HOME, использовать отдельное состояние OFFLINE с чёрным фоном согласно ТЗ §7.
Комментарии на русском языке.

---

### ДЕНЬ 11 — Буфер Serial / стабилизация

---

### 📌 ТЕБЕ — Стресс-тест (запусти на 30 минут)
- [ ] Данные обновляются на дисплее каждую секунду
- [ ] Нет зависаний ESP32
- [ ] Выключи USB от ПК на 10 сек → ESP32 показывает "PC OFFLINE"
- [ ] Подключи обратно → автоматически восстановился на последнем экране
- [ ] Перезапусти Python (Ctrl+C → запуск снова) → Handshake сработал без перезагрузки ESP32
- [ ] В консоли Python нет необработанных исключений

Если что-то не так — используй промт 11.1.

---

### 🟦 DEEPSEEK — Промт 11.1: Диагностика Serial (шаблон)

Проект GameDesk. Проблема с Serial между Python и ESP32.

Симптомы: [ОПИШИ ТОЧНО — данные не приходят / зависает / мусор / и т.д.]

Конфигурация:
- Python: pyserial, 115200 baud, пакеты вида <KEY=VALUE;...>\n
- ESP32: Arduino, буфер 1024 байт, парсинг после получения '>'
- Handshake: Python шлёт <CMD=PING>, ESP32 отвечает <CMD=PONG;DEVICE=GAMEDECK;VER=1>

Код Python serial_sender.py:
[ВСТАВЬ КОД]

Код ESP32 serial_handler.cpp:
[ВСТАВЬ КОД]

Найди причину и предложи исправление.

---

## ═══════════════════════════════════
## PHASE 5-6 — Telemetry + Statistics
## ═══════════════════════════════════

---

### ДЕНЬ 12 — Телеметрия CPU/GPU/RAM

---

### 📌 ТЕБЕ — Важно перед промтом
LibreHardwareMonitor требует запуска от администратора.
Открой VS Code правой кнопкой → "Запустить от имени администратора".
Установи pythonnet: pip install pythonnet

---

### 🟦 DEEPSEEK — Промт 12.1: telemetry.py

Проект GameDesk, Python. Файл telemetry.py.

Класс TelemetryReader:

get_telemetry() → dict с ключами cpu_temp, gpu_temp, ram_usage (int или -1):
- Использовать LibreHardwareMonitor через pythonnet/clr и WMI
- CPU temp: сенсор Temperature с "CPU Package" или "CPU" в имени
- GPU temp: сенсор Temperature с "GPU Core" или "GPU"  
- RAM usage: сенсор Load с "Memory" ИЛИ через psutil.virtual_memory().percent (как запасной вариант)
- Кэшировать результат на 2 секунды
- Если LibreHardwareMonitor не доступен → вернуть все -1
- НИКОГДА не крашить программу из-за телеметрии — только логировать ошибки

Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 12.2: Интеграция телеметрии в main.py

Проект GameDesk, Python.

В главном цикле main.py добавь:
1. telemetry = TelemetryReader() при старте
2. В каждой итерации: data = telemetry.get_telemetry()
3. Передавать cpu=data["cpu_temp"], gpu=data["gpu_temp"], ram=data["ram_usage"] в build_data_packet()
4. В консольном статусе: если значение -1 → показывать "--" вместо числа

Больше ничего не менять — это просто дополнительные поля в уже рабочем пакете.

---

### ДЕНЬ 13 — LIST-пакет + RECENT GAMES на ESP32

---

### 🟦 DEEPSEEK — Промт 13.1: Парсинг LIST на ESP32

Проект GameDesk, ESP32. Доработка serial_handler.cpp.

Добавь полноценный парсинг LIST-пакета:

При получении <LIST=RECENT;COUNT=N>:
- Начать буферизацию LIST, создать временный массив GameEntry tempList[10], int tempCount=0
- Запомнить время начала буферизации

При получении <GAME=name;TOTAL=...;LAST=...;WEEK=...;MONTH=...> внутри LIST:
- Добавить в tempList если tempCount < 10
- Парсить поля: NAME, TOTAL, LAST, WEEK, MONTH

При получении </LIST>:
- Скопировать tempList в основной gameList[]
- gameListCount = tempCount
- Установить флаг hasNewList = true
- Вызвать onNewListReceived()

Если с момента <LIST=...> прошло > 500 мс и </LIST> так и не получен:
- Выбросить tempList, не применять к UI
- Если DEBUG: вывести "[ERR] LIST timeout, discarded"

ESP32 НИКОГДА не сортирует и не фильтрует — только хранит и отображает.
Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 13.2: Экран RECENT GAMES (финальный)

Проект GameDesk, ESP32, дисплей ST7789V 320x240, библиотека TFT_eSPI.

Реализуй финальную отрисовку экрана RECENT GAMES.

Макет:
- Заголовок "RECENT GAMES" вверху, шрифт 2, белый
- Список игр: каждая строка 35 пикселей высотой
- Видимо до 6 игр одновременно
- Активная (выбранная) строка: синий фон, белый текст
- Остальные: тёмный фон, серый текст
- Слева номер "1." "2." и т.д., справа время "14:23" (TOTAL в формате HH:MM)
- Если список пуст: по центру серым "Нет данных"
- Скролл-индикатор справа если игр > 6

Функции:
- void drawRecentGames(GameEntry* games, int count, int selectedIndex, int scrollOffset)
- void recentGamesScrollUp()
- void recentGamesScrollDown()
- int getSelectedIndex()

Частичное обновление при навигации: только строки которые изменили состояние.
Комментарии на русском языке.

---

## ═══════════════════════════════════
## PHASE 7 — Recent Games + Detail View
## ═══════════════════════════════════

---

### ДЕНЬ 14 — Detail View + HOME финальный

---

### 🟦 DEEPSEEK — Промт 14.1: Экран DETAIL VIEW

Проект GameDesk, ESP32, дисплей ST7789V 320x240.

Реализуй экран DETAIL VIEW в display_manager.cpp.

Источник данных: snapshot из gameList[selectedIndex] — данные из последнего LIST-пакета.
Это НЕ live-данные. Обновляется только при получении нового LIST.

Макет:
- Вверху: название игры, шрифт 4, белый
- Горизонтальная разделительная линия
- "Total:  " + total время, жёлтым
- "Week:   " + weekly время, зелёным
- "Month:  " + monthly время, синим
- "Last:   " + дата последнего запуска, серым
- Внизу мелко: "← назад   (CENTER долгое=настройки)"

Значения "-1" (недоступно) показывать как "--" серым.

Функция: void drawDetailView(const GameEntry& game)

Выход обрабатывается в state_machine (LEFT → RECENT_GAMES, CENTER долгое → SETTINGS).
При возврате в RECENT GAMES восстанавливать selectedIndex.
Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 14.2: Экран HOME финальный + частичное обновление таймера

Проект GameDesk, ESP32, дисплей ST7789V 320x240, библиотека TFT_eSPI.

Реализуй финальный экран HOME.

Макет:
- Верхняя строка: "GAMEDESK" шрифт 1, серый
- Центр: название игры шрифт 4, белый (если нет игры — "Нет активной игры" серым шрифтом 2)
- Под названием: таймер сессии "01:23:45" шрифт 4, жёлтый (если нет сессии — не показывать)
- Снизу: подсказка-навигация мелко серым "← MON | STA | REC →"

Частичное обновление:
- Таймер обновляется каждую секунду: стереть только область таймера (залить фоном), нарисовать новое значение
- Название игры перерисовывается только при смене игры

Функции:
- void drawHome(const char* gameName, const char* sessionTime)
- void updateHomeTimer(const char* sessionTime)  // только область таймера

Комментарии на русском языке.

---

### ДЕНЬ 15 — Полный интеграционный тест

---

### 📌 ТЕБЕ — Сквозной тест Phase 7
1. Запусти Python с реальными играми
2. Открой одну из игр из config.py → HOME должен показать название и растущий таймер
3. RIGHT/LEFT → RECENT GAMES → подожди LIST-пакет (до 30 сек) → список обновится
4. UP/DOWN → навигация по списку
5. Tap на игре → DETAIL VIEW → проверь все поля
6. LEFT → обратно в RECENT GAMES на том же элементе
7. CENTER долгое → SETTINGS → Connection Status → "Connected / VER=1"
8. Выключи Python → "PC OFFLINE" → включи → восстановился на последнем экране

---

## ═══════════════════════════════════
## PHASE 8 — FPS (опционально, не блокирует релиз)
## ═══════════════════════════════════

---

### ДЕНЬ 16 — Попытка FPS через RTSS

---

### 📌 ТЕБЕ
Если за час не заработало — пропускай. FPS=-1 уже корректно обрабатывается везде.

---

### 🟦 DEEPSEEK — Промт 16.1: FPS через RTSS shared memory

Проект GameDesk, Python. Функция get_fps() в telemetry.py.

RTSS (RivaTuner Statistics Server) предоставляет FPS через Windows Shared Memory.
Найди рабочий Python-пример чтения FPS из RTSS Shared Memory на Windows.
Если RTSS не запущен или не установлен → вернуть -1.
Если RTSS недоступен → попробовать PresentMon через subprocess как резерв.
Если оба недоступны → вернуть -1, не крашить.

Функция get_fps() → int (FPS) или -1.
Интегрировать в TelemetryReader, передавать в build_data_packet(fps=...).
Комментарии на русском языке.

---

## ═══════════════════════════════════
## PHASE 9-10 — UI Polish + Settings
## ═══════════════════════════════════

---

### ДЕНЬ 17 — UI Polish: anti-flicker + цветовая схема

---

### 🟦 DEEPSEEK — Промт 17.1: Система частичного обновления

Проект GameDesk, ESP32, дисплей ST7789V 320x240, библиотека TFT_eSPI.

Реализуй универсальную функцию обновления числовых значений без мерцания.

Проблема: при перерисовке числа заливка фоном и новый текст вызывают мерцание.

Решение — функция updateValue():
void updateValue(int x, int y, const char* newVal, char* cachedVal, uint16_t bgColor, uint16_t fgColor, uint8_t font, int maxWidth)
- Если newVal == cachedVal → ничего не делать (return)
- Иначе: tft.fillRect(x, y, maxWidth, fontHeight, bgColor) — стереть старое
- tft.drawString(newVal, x, y) — нарисовать новое
- Обновить cachedVal = newVal

Применить для:
- Таймера сессии на HOME (updateHomeTimer)
- CPU температуры на MONITOR
- GPU температуры на MONITOR
- RAM % на MONITOR
- Всех значений на STATS

fillScreen() использовать ТОЛЬКО при смене экрана, никогда при обновлении данных.
Комментарии на русском языке.

---

### 🟦 DEEPSEEK — Промт 17.2: Финальная цветовая схема

Проект GameDesk, ESP32, дисплей ST7789V 320x240 (65K RGB565 цвета).

Разработай финальную тёмную тему интерфейса.

Требования:
- Фон: очень тёмный (не чистый чёрный — чтобы рамки были видны)
- Основной текст: белый
- Акцент / таймер: ярко-жёлтый или оранжевый
- CPU температура: оранжево-красный (тепло = опасность)
- GPU температура: зелёный
- RAM использование: синий
- Серый для подписей и неактивных элементов
- Синий фон для активного/выбранного элемента
- Красный для OFFLINE и ошибок
- Тёмно-серый для разделителей

Выдай таблицу: название → HEX → RGB565 hex для TFT_eSPI → где используется.
Обнови config.h — добавь все цвета как #define COLOR_XXX 0xXXXX.
Комментарии на русском языке.

---

### ДЕНЬ 18 — Финальная полировка SETTINGS

---

### 🟦 DEEPSEEK — Промт 18.1: Connection Status с реальными данными

Проект GameDesk, ESP32. Доработка Connection Status в SETTINGS.

Нужны реальные данные, не заглушки.

Структура в serial_handler.h:
struct ConnectionStatus {
  bool connected;
  int protocolVer;
  unsigned long lastPacketMs;  // millis() момента последнего валидного пакета
  unsigned long uptimeMs;      // millis() — время работы с момента загрузки
};
extern ConnectionStatus connStatus;

serial_handler.cpp: обновлять connStatus при каждом валидном пакете.

display_manager.cpp — в drawSettingsConnectionStatus():
- Device: Connected / Offline
- Protocol: VER=1
- Last packet: вычислить (millis() - connStatus.lastPacketMs) / 1000 → "X sec ago"
- Uptime: connStatus.uptimeMs / 1000 → форматировать как "HH:MM:SS"

Комментарии на русском языке.

---

## ═══════════════════════════════════
## PHASE 11 — Release 1.0
## ═══════════════════════════════════

---

### ДНИ 19-22 — Финальное тестирование

---

### 📌 ТЕБЕ — Финальный чеклист Release 1.0 (ТЗ §17)

Загрузка и подключение:
- [ ] ESP32 загружается <= 4 секунд, виден логотип и progress bar
- [ ] Python находит ESP32 автоматически через PING/PONG (никакого хардкода порта)

Основная функциональность:
- [ ] Запусти игру из config.py → HOME показывает название и растущий таймер
- [ ] LEFT/RIGHT: HOME → MONITOR → STATS → RECENT GAMES → HOME
- [ ] MONITOR: CPU°C / GPU°C / RAM% (или "--" если недоступно)
- [ ] STATS: недельное и месячное время обновляются

Recent Games и Detail View:
- [ ] RECENT GAMES: список от Python, отсортирован по дате
- [ ] UP/DOWN прокручивают список, активный элемент подсвечен
- [ ] CENTER короткое на игре → DETAIL VIEW с данными snapshot
- [ ] Поля -1 в DETAIL VIEW → показываются как "--"
- [ ] LEFT из DETAIL VIEW → обратно в RECENT GAMES на тот же элемент
- [ ] CENTER долгое из DETAIL VIEW → SETTINGS

OFFLINE:
- [ ] Выключи Python → через 5 сек "PC OFFLINE" на HOME
- [ ] LEFT/RIGHT/UP/DOWN не работают пока OFFLINE
- [ ] Включи Python → автоматически восстановился на последнем активном экране

SETTINGS:
- [ ] CENTER долгое из любого экрана → SETTINGS
- [ ] Connection Status: реальные данные (connected, ver, last packet, uptime)
- [ ] Restart Device: запрашивает подтверждение, перезагружает ESP32
- [ ] About: FW: 1.0 / ESP32-32S NodeMCU / ST7789V
- [ ] Exit и CENTER долгое → выходят из SETTINGS

Технические:
- [ ] DEBUG MODE: удержание CENTER при загрузке → Serial Monitor показывает лог
- [ ] Нет мерцания при обновлении значений (частичное обновление работает)
- [ ] Нет зависаний за 3-4 часа непрерывной работы
- [ ] Ctrl+C в Python → статистика сохранена в games.json

---

### 🟦 DEEPSEEK — Промт финальный: исправление любого бага

Проект GameDesk (ESP32 + Python). Финальное тестирование перед Release 1.0.

Баг: [ОПИШИ ЧТО ПРОИСХОДИТ И ЧТО ДОЛЖНО ПРОИСХОДИТЬ]
Шаги воспроизведения: [ОПИШИ]

Среда:
- NodeMCU ESP-32S, Arduino IDE, библиотека TFT_eSPI
- Python 3.x, psutil + pyserial + pythonnet
- Протокол GameDesk VER=1, пакеты <KEY=VALUE;...>

Файл где предположительно баг:
[ВСТАВЬ КОД]

Найди и исправь. Объясни причину на русском языке.

---

### ДЕНЬ 23 — RELEASE 1.0

---

### 📌 ТЕБЕ — Действия в день релиза

1. Сохрани финальную прошивку ESP32: Sketch → Export Compiled Binary → сохрани .bin файл
2. Создай архив: gamedesk_pc_v1.0.zip с Python-проектом
3. Проверь games.json — статистика накоплена корректно
4. Запиши в BACKLOG.md всё что хотел добавить но не успел
5. Обнови Roadmap.md — все фазы отметь как DONE
6. Сделай фото или видео работающей системы — заслужил!

---

### 🟩 GIGACODE — Создай BACKLOG.md

Создай файл BACKLOG.md в корне проекта со структурой:

# GameDesk Backlog

## v1.1 (запланировано по Roadmap)
- Рассмотреть добавление тачскрина (если будет найдена плата с распаянным XPT2046)
- Brightness регулировка в SETTINGS (если LED на GPIO)
- Display Settings (анимации, загрузочный логотип)
- Reset Device в SETTINGS
- Стабилизация FPS через RTSS
- Графики нагрузки CPU/GPU на экране MONITOR

## v2.0 (перспектива)
- Wi-Fi режим (подключение без USB)
- Веб-интерфейс для просмотра статистики
- OTA обновления прошивки ESP32

## Мои идеи (появились в процессе разработки)
- [сюда записывай всё что придумал]

---

## ═══════════════════════════════════
## БЫСТРЫЕ ПРОМТЫ — на любой день
## ═══════════════════════════════════

---

### 🟦 DEEPSEEK — Объяснение концепции

Проект GameDesk, ESP32 + Python. Объясни на русском языке простыми словами:
[ВОПРОС]

Контекст: тонкий клиент на ESP32 (дисплей ST7789V 320x240, 5 кнопок), ПК на Python, USB Serial, протокол пакетами вида <KEY=VALUE;...>.

---

### 🟦 DEEPSEEK — Рефакторинг с ограничениями

Проект GameDesk. Вот мой код файла [ФАЙЛ]:
[КОД]

Что хочу улучшить: [ОПИСАНИЕ]

Ограничения которые НЕЛЬЗЯ нарушать:
- ESP32 не хранит бизнес-логику, только отображает
- Парсинг пакетов только после получения символа '>'
- Буфер Serial >= 1024 байт
- Частота отправки не выше 10 Гц
- Время сессии считает только Python
- ESP32 никогда не сортирует и не фильтрует данные

Перепиши с учётом ограничений. Комментарии на русском.

---

### 🟩 GIGACODE — Аудит проекта

Посмотри на текущую структуру проекта и найди:
1. Файлы которые объявлены в include/import но не используются
2. Дублирующийся код между файлами
3. Захардкоженные значения которые должны быть в config.h или config.py
4. Потенциальные утечки памяти в C++ файлах (массивы без ограничения размера)
Предложи конкретные исправления.

