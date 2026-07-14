#include "serial_handler.h"
#include <string.h>

// -------------------- Внешние функции --------------------
extern void onAppShutdown();
extern void onSerialLost();
extern void onSerialRestored();

// -------------------- Глобальные переменные --------------------
extern bool debugMode;

ParsedData parsedData;                 // данные текущего пакета
GameEntry gameList[MAX_GAMES];         // основной список последних игр (актуальный)
int gameCount = 0;
StatsSummary statsSummary;             // сводная статистика для экрана STATS

// -------------------- Статус соединения (Phase 4/6) --------------------
// connected/ver обновляются при КАЖДОМ валидном пакете (DATA, LIST, STATS, HB),
// а не только при хендшейке — иначе Connection Status зависает в Offline
// даже если данные реально идут.
static bool connConnected = false;
static int  connVer = 0;

// -------------------- Статические переменные модуля --------------------
static char rxBuffer[1024];           // буфер для накопления байт с Serial
static int rxIndex = 0;

static char currentPacket[MAX_PACKET_SIZE + 1];
static int packetIndex = 0;            // не используется

static bool listMode = false;          // флаг: находимся в режиме сбора LIST
static unsigned long listStartTime = 0;
static const unsigned long LIST_TIMEOUT_MS = 500;

static GameEntry tempList[MAX_GAMES];  // временный список для текущего LIST
static int tempCount = 0;

static unsigned long lastPacketTime = 0;
static bool wasOffline = false;

static const unsigned long OFFLINE_TIMEOUT_MS = 5000; // 5 секунд

// -------------------- Вспомогательные функции --------------------

// Отправка строки через Serial (с переводом строки)
static void sendSerial(const char* str) {
    Serial.print(str);
    Serial.print('\n');
}

// Преобразование "HH:MM" или "HH:MM:SS" в секунды
static int timeToSeconds(const char* str) {
    int h, m, s = 0;
    if (sscanf(str, "%d:%d:%d", &h, &m, &s) == 3) {
        return h * 3600 + m * 60 + s;
    }
    if (sscanf(str, "%d:%d", &h, &m) == 2) {
        return h * 3600 + m * 60;
    }
    return 0;
}

// Извлекает значение поля VER=N из любого пакета (DATA, HB, и т.п.), если оно есть.
// Согласно ТЗ §6.2 VER не обязателен в каждом пакете, поэтому просто игнорируем,
// если поле отсутствует — предыдущее значение connVer не трогаем.
static void extractVerIfPresent(const char* packet) {
    const char* p = strstr(packet, "VER=");
    if (p != NULL) {
        connVer = atoi(p + 4);
    }
}

// Парсинг сводного пакета STATS: <STATS;WEEK=HH:MM;MONTH=HH:MM;GAMES=N>
static void parseStatsPacket(const char* packet) {
    const char* start = packet;
    if (*start == '<') start++;
    const char* end = packet + strlen(packet) - 1;
    if (*end == '>') end--;

    char temp[128];
    size_t len = end - start + 1;
    if (len >= sizeof(temp)) len = sizeof(temp) - 1;
    strncpy(temp, start, len);
    temp[len] = '\0';

    int week = -1, month = -1, games = -1;

    char* token = strtok(temp, ";");
    while (token != NULL) {
        if (strncmp(token, "WEEK=", 5) == 0) {
            week = timeToSeconds(token + 5);
        } else if (strncmp(token, "MONTH=", 6) == 0) {
            month = timeToSeconds(token + 6);
        } else if (strncmp(token, "GAMES=", 6) == 0) {
            games = atoi(token + 6);
        }
        token = strtok(NULL, ";");
    }

    statsSummary.weekly_sec = week;
    statsSummary.monthly_sec = month;
    statsSummary.totalGames = games;
    statsSummary.hasData = true;

    if (debugMode) {
        Serial.print("[DEBUG] STATS parsed: WEEK_sec=");
        Serial.print(week);
        Serial.print(" MONTH_sec=");
        Serial.print(month);
        Serial.print(" GAMES=");
        Serial.println(games);
    }
}

// Парсинг одиночного DATA-пакета (с поддержкой heartbeat)
static void parseSinglePacket(const char* packet) {
    const char* start = packet;
    if (*start == '<') start++;
    const char* end = packet + strlen(packet) - 1;
    if (*end == '>') end--;

    char temp[256];
    size_t len = end - start + 1;
    if (len >= sizeof(temp)) len = sizeof(temp) - 1;
    strncpy(temp, start, len);
    temp[len] = '\0';

    bool hasGame = false, hasSession = false, hasState = false;

    char* token = strtok(temp, ";");
    while (token != NULL) {
        if (strncmp(token, "GAME=", 5) == 0) {
            strncpy(parsedData.game, token + 5, sizeof(parsedData.game) - 1);
            parsedData.game[sizeof(parsedData.game) - 1] = '\0';
            hasGame = true;
        } else if (strncmp(token, "SESSION=", 8) == 0) {
            strncpy(parsedData.session, token + 8, sizeof(parsedData.session) - 1);
            parsedData.session[sizeof(parsedData.session) - 1] = '\0';
            hasSession = true;
        } else if (strncmp(token, "STATE=", 6) == 0) {
            strncpy(parsedData.state, token + 6, sizeof(parsedData.state) - 1);
            parsedData.state[sizeof(parsedData.state) - 1] = '\0';
            hasState = true;
        } else if (strncmp(token, "FPS=", 4) == 0) {
            parsedData.fps = atoi(token + 4);
        } else if (strncmp(token, "CPU=", 4) == 0) {
            parsedData.cpu = atoi(token + 4);
        } else if (strncmp(token, "GPU=", 4) == 0) {
            parsedData.gpu = atoi(token + 4);
        } else if (strncmp(token, "RAM=", 4) == 0) {
            parsedData.ram = atoi(token + 4);
        }
        token = strtok(NULL, ";");
    }

    // Если это heartbeat (STATE=IDLE без GAME и SESSION) — сбрасываем данные
    if (hasState && strcmp(parsedData.state, "IDLE") == 0 && !hasGame && !hasSession) {
        strcpy(parsedData.game, "NONE");
        strcpy(parsedData.session, "00:00:00");
        // parsedData.state уже "IDLE"
    }

    parsedData.hasNewData = true;
    if (debugMode) {
        Serial.print("[DEBUG] Parsed DATA: GAME=");
        Serial.print(parsedData.game);
        Serial.print(" SESSION=");
        Serial.print(parsedData.session);
        Serial.print(" STATE=");
        Serial.println(parsedData.state);
    }
}

// Парсинг одной строки <GAME=...> и добавление во временный список
static void addGameEntry(const char* line) {
    if (tempCount >= MAX_GAMES) {
        if (debugMode) Serial.println("[DEBUG] tempList overflow, ignoring game");
        return;
    }

    char temp[256];
    strncpy(temp, line, sizeof(temp) - 1);
    temp[sizeof(temp) - 1] = '\0';
    char* p = temp;
    if (*p == '<') p++;
    char* endp = p + strlen(p) - 1;
    if (*endp == '>') *endp = '\0';

    GameEntry entry;
    memset(&entry, 0, sizeof(entry));

    char* token = strtok(p, ";");
    while (token != NULL) {
        if (strncmp(token, "GAME=", 5) == 0) {
            strncpy(entry.name, token + 5, sizeof(entry.name) - 1);
            entry.name[sizeof(entry.name) - 1] = '\0';
        } else if (strncmp(token, "TOTAL=", 6) == 0) {
            entry.total_sec = timeToSeconds(token + 6);
        } else if (strncmp(token, "LAST=", 5) == 0) {
            strncpy(entry.last_played, token + 5, sizeof(entry.last_played) - 1);
            entry.last_played[sizeof(entry.last_played) - 1] = '\0';
        } else if (strncmp(token, "WEEK=", 5) == 0) {
            entry.weekly_sec = timeToSeconds(token + 5);
        } else if (strncmp(token, "MONTH=", 6) == 0) {
            entry.monthly_sec = timeToSeconds(token + 6);
        }
        token = strtok(NULL, ";");
    }

    if (strlen(entry.name) > 0) {
        tempList[tempCount++] = entry;
        if (debugMode) {
            Serial.print("[DEBUG] Added game: ");
            Serial.println(entry.name);
        }
    }
}

// Обработка полученного пакета (строка между '<' и '>')
static void processPacket(const char* packet) {
    size_t len = strlen(packet);
    if (len < 2 || packet[0] != '<' || packet[len-1] != '>') {
        if (debugMode) {
            Serial.print("[DEBUG] Invalid packet. Content: ");
            Serial.println(packet);
        }
        return;
    }

    // Обновляем время последнего пакета и статус соединения.
    // ВАЖНО: это должно происходить для ЛЮБОГО валидного пакета (DATA, LIST, STATS, HB,
    // CMD=PING), а не только при хендшейке — иначе Connection Status будет вечно
    // показывать Offline, даже если данные реально идут.
    lastPacketTime = millis();
    connConnected = true;
    extractVerIfPresent(packet);

    // Если были в OFFLINE, уведомляем о восстановлении
    if (wasOffline) {
        wasOffline = false;
        onSerialRestored();
    }

    // Обработка PING
    if (strcmp(packet, "<CMD=PING>") == 0) {
        if (debugMode) Serial.println("[DEBUG] Received PING, sending PONG");
        sendPong();
        return;
    }

    // Обработка STATS (сводная статистика для экрана STATS, Phase 6)
    if (strncmp(packet, "<STATS", 6) == 0) {
        parseStatsPacket(packet);
        return;
    }

    // Обработка SHUTDOWN
    if (strcmp(packet, "<CMD=SHUTDOWN>") == 0) {
        if (debugMode) Serial.println("[DEBUG] Received SHUTDOWN");
        onAppShutdown();
        return;
    }

    // Обработка LIST
    if (strncmp(packet, "<LIST=RECENT", 12) == 0) {
        // Начинаем новый LIST – сбрасываем временный список
        if (listMode) {
            if (debugMode) Serial.println("[DEBUG] Warning: new LIST while previous not closed");
            tempCount = 0;
        }
        listMode = true;
        tempCount = 0;
        listStartTime = millis();
        parsedData.hasNewList = false;
        if (debugMode) Serial.println("[DEBUG] LIST started");
        return;
    }

    // Если мы в режиме LIST
    if (listMode) {
        // Проверяем закрывающий тег
        if (strcmp(packet, "</LIST>") == 0) {
            listMode = false;
            // Копируем временный список в основной
            gameCount = tempCount;
            memcpy(gameList, tempList, sizeof(GameEntry) * tempCount);
            parsedData.hasNewList = true;
            if (debugMode) {
                Serial.print("[DEBUG] LIST closed, count=");
                Serial.println(gameCount);
            }
            // Уведомляем UI (отрисовка RECENT GAMES) — будет обработано в loop()
            return;
        }

        // Если строка начинается с "<GAME=", добавляем в tempList
        if (strncmp(packet, "<GAME=", 6) == 0) {
            addGameEntry(packet);
            return;
        }

        // Игнорируем другие строки внутри LIST
        if (debugMode) {
            Serial.print("[DEBUG] Unexpected line inside LIST: ");
            Serial.println(packet);
        }
        return;
    }

    // Обработка DATA / HEARTBEAT (одиночный пакет)
    if (strstr(packet, "STATE=") != NULL) {
        parseSinglePacket(packet);
    } else {
        if (debugMode) {
            Serial.print("[DEBUG] Unknown packet: ");
            Serial.println(packet);
        }
    }
}

// -------------------- Публичные функции --------------------

void serialHandlerInit() {
    Serial.begin(115200);
    memset(&parsedData, 0, sizeof(parsedData));
    parsedData.fps = -1;
    parsedData.cpu = -1;
    parsedData.gpu = -1;
    parsedData.ram = -1;
    strcpy(parsedData.state, "IDLE");
    parsedData.hasNewData = false;
    parsedData.hasNewList = false;

    gameCount = 0;
    memset(gameList, 0, sizeof(gameList));

    statsSummary.weekly_sec = -1;
    statsSummary.monthly_sec = -1;
    statsSummary.totalGames = -1;
    statsSummary.hasData = false;

    tempCount = 0;
    listMode = false;
    lastPacketTime = millis();
    wasOffline = false;
    connConnected = false;
    connVer = 0;
}

void serialHandlerUpdate() {
    // 1. Проверка таймаута LIST
    if (listMode && (millis() - listStartTime > LIST_TIMEOUT_MS)) {
        if (debugMode) Serial.println("[DEBUG] LIST timeout, discarding");
        listMode = false;
        tempCount = 0;
        parsedData.hasNewList = false;
    }

    // 2. Проверка потери связи (OFFLINE)
    if (!wasOffline && (millis() - lastPacketTime > OFFLINE_TIMEOUT_MS)) {
        wasOffline = true;
        onSerialLost();
        if (debugMode) Serial.println("[DEBUG] OFFLINE detected");
    }

    // 3. Чтение данных из Serial
    while (Serial.available() > 0) {
        char c = Serial.read();

        // ---- Игнорируем символы до '<' ----
        if (rxIndex == 0 && c != '<') {
            // Если это не '<' и буфер пуст — пропускаем
            continue;
        }

        if (rxIndex >= sizeof(rxBuffer) - 1) {
            rxIndex = 0;
            if (debugMode) Serial.println("[DEBUG] rxBuffer overflow, reset");
            continue;
        }

        rxBuffer[rxIndex++] = c;

        if (c == '>') {
            rxBuffer[rxIndex] = '\0';

            if (rxIndex >= 2) {
                strncpy(currentPacket, rxBuffer, sizeof(currentPacket) - 1);
                currentPacket[sizeof(currentPacket) - 1] = '\0';
                processPacket(currentPacket);
            } else {
                if (debugMode) Serial.println("[DEBUG] Empty packet ignored");
            }

            rxIndex = 0;
        }
    }
}

bool isSerialDataAvailable() {
    return parsedData.hasNewData || parsedData.hasNewList;
}

void clearSerialDataFlag() {
    parsedData.hasNewData = false;
    parsedData.hasNewList = false;
}

void sendPong() {
    sendSerial("<CMD=PONG;DEVICE=GAMEDECK;VER=1>");
}

void resetOfflineTimer() {
    // ВАЖНО: раньше здесь стояло lastPacketTime = millis() + OFFLINE_TIMEOUT_MS + 10000,
    // то есть время выставлялось В БУДУЩЕЕ. Из-за этого в следующей же проверке
    // (millis() - lastPacketTime > OFFLINE_TIMEOUT_MS) арифметика unsigned long
    // переполнялась и условие сразу становилось истинным — устройство мгновенно
    // переходило в OFFLINE поверх только что установленного WAITING.
    //
    // Правильное поведение: это осознанное отключение (получили <CMD=SHUTDOWN>),
    // поэтому мы просто сразу помечаем состояние "уже офлайн", без арифметики
    // с будущим временем — тогда serialHandlerUpdate() не будет повторно
    // вызывать onSerialLost() поверх WAITING.
    lastPacketTime = millis();
    wasOffline = true;
    connConnected = false;
    if (debugMode) Serial.println("[DEBUG] Offline timer reset (manual disconnect)");
}

ConnectionInfo getConnectionInfo() {
    ConnectionInfo info;
    info.connected = connConnected && !wasOffline;
    info.ver = connVer;
    info.lastPacketMs = lastPacketTime;
    return info;
}