#ifndef SERIAL_HANDLER_H
#define SERIAL_HANDLER_H

#include <Arduino.h>

// Максимальные размеры буферов (согласно ТЗ)
#define MAX_PACKET_SIZE 256        // для одиночного пакета
#define MAX_LIST_SIZE   512        // для всего LIST-пакета
#define MAX_GAMES       10         // максимум игр в списке

// Структура для хранения текущих данных с ПК (одиночный пакет)
struct ParsedData {
  char game[32];           // название игры
  char session[10];        // время сессии HH:MM:SS
  char state[10];          // RUNNING / IDLE / OFFLINE
  int  fps;                // кадры/с или -1
  int  cpu;                // температура CPU или -1
  int  gpu;                // температура GPU или -1
  int  ram;                // использование RAM % или -1
  bool hasNewData;         // флаг, что пришли свежие DATA
  bool hasNewList;         // флаг, что пришёл новый LIST (добавлено)
};

// Структура одной записи для списка RECENT GAMES
struct GameEntry {
  char name[32];           // название игры
  int  total_sec;          // общее время (сек)
  char last_played[11];    // дата YYYY-MM-DD
  int  weekly_sec;         // за неделю (сек)
  int  monthly_sec;        // за месяц (сек)
};

// Сводная статистика для экрана STATS (Phase 6)
// Приходит отдельным пакетом <STATS;WEEK=HH:MM;MONTH=HH:MM;GAMES=N>
struct StatsSummary {
  int  weekly_sec;         // суммарное время за неделю по всем играм (сек), -1 = нет данных
  int  monthly_sec;        // суммарное время за месяц по всем играм (сек), -1 = нет данных
  int  totalGames;         // количество игр в games.json, -1 = нет данных
  bool hasData;            // был ли вообще получен хоть один STATS-пакет
};

// Статус соединения с ПК (используется экраном SETTINGS -> Connection Status)
struct ConnectionInfo {
  bool connected;                 // true, если пакеты приходят регулярно (не OFFLINE)
  int  ver;                       // последняя полученная версия протокола (VER=)
  unsigned long lastPacketMs;     // millis() момента последнего валидного пакета
};

// Глобальные переменные, доступные из UI
extern ParsedData parsedData;
extern GameEntry gameList[MAX_GAMES];
extern int gameCount;          // количество записей в gameList
extern StatsSummary statsSummary;
extern bool debugMode;         // режим отладки (устанавливается из GameDesk_ESP32.ino)

// Инициализация обработчика (настраивает Serial, таймеры)
void serialHandlerInit();

// Основной цикл обработки – вызывать в loop() как можно чаще
void serialHandlerUpdate();

// Проверка наличия новых данных (hasNewData или hasNewList)
bool isSerialDataAvailable();

// Сброс флага hasNewData и hasNewList после чтения данных UI
void clearSerialDataFlag();

// Отправка ответа PONG (используется при получении PING)
void sendPong();

// Сбросить таймер последнего пакета (чтобы не уходить в OFFLINE)
void resetOfflineTimer();

// Текущий статус соединения (для экрана SETTINGS -> Connection Status).
// Вызывать из loop() каждую итерацию и прокидывать в display.setConnectionStatus().
ConnectionInfo getConnectionInfo();

#endif