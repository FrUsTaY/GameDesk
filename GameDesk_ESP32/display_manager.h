// ====================================================================
// display_manager.h — управление дисплеем GameDesk
// Версия: 5.1 — добавлена поддержка RECENT GAMES с навигацией
// ====================================================================

#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <TFT_eSPI.h>
#include "config.h"
#include "state_machine.h"
#include "button_handler.h"
#include "serial_handler.h"   // для GameEntry, gameList, gameCount

// Примечание: структура статуса соединения (ConnectionInfo) теперь определена
// в serial_handler.h — она же обновляется в serial_handler.cpp при каждом
// валидном пакете. Здесь просто используем её, чтобы не было двух источников
// истины (раньше DisplayManager держал свою копию, которая никогда не обновлялась).

class DisplayManager {
public:
    DisplayManager(TFT_eSPI& tft);
    void init();
    void drawScreen(UIState state);

    // Boot-последовательность
    void startBoot();
    bool updateBoot();

    // SETTINGS: обработка событий внутри меню
    bool handleSettingsEvent(ButtonEvent event);

    // Обновление статуса соединения. Вызывать из loop() каждую итерацию:
    //   display.setConnectionStatus(getConnectionInfo());
    void setConnectionStatus(const ConnectionInfo& status);

    // Публичные методы отрисовки экранов
    void drawHome();
    void updateHomeTimer(); // обновить только таймер на HOME (вызывать каждую секунду)
    void drawMonitor();
    void drawStats();
    void drawRecentGames();          // рисует весь экран
    void drawDetailView();
    void drawSettings();
    void drawOffline();
    void drawWaiting();               // экран ожидания приложения
    void refreshScreen();             // принудительное обновление текущего экрана

    // Навигация по RECENT GAMES
    void recentGamesScrollUp();      // выбор предыдущей игры
    void recentGamesScrollDown();    // выбор следующей игры
    int getRecentSelectedIndex() const;
    void resetRecentGamesState();    // сброс при входе в экран

private:
    TFT_eSPI& _tft;
    UIState _lastState;

    // Boot-переменные
    unsigned long _bootStartTime;
    unsigned long _lastProgressUpdate;
    int _fadeStep;          // текущий шаг логотипа (-1 = не нарисован, 0..4)
    float _progress;
    bool _bootComplete;
    int _lastProgressFill;  // последняя заполненная ширина прогресс-бара (px)

    // SETTINGS
    enum SettingsSubState {
        MAIN_MENU,
        CONN_INFO,
        ABOUT_INFO,
        RESTART_CONFIRM
    };
    SettingsSubState _settingsSubState;
    int _settingsSelectedIndex;
    ConnectionInfo _connStatus;

    // RECENT GAMES состояние
    int _recentSelectedIndex;   // индекс выбранной игры (0..gameCount-1)
    int _recentScrollOffset;    // смещение для скролла (сколько игр пропущено сверху)
    static const int MAX_VISIBLE_ITEMS = 6;   // максимум видимых строк

    void resetSettings();

    // HOME — для частичного обновления таймера
    char _lastGameName[32];          // последнее отображённое имя игры
    unsigned long _lastTimerUpdate;  // время последнего обновления таймера (ms)
    bool _isTimerActive;             // флаг, что таймер активен (есть сессия)

    // Вспомогательные методы отрисовки
    void drawHeader(const char* title);
    void drawCenteredText(const char* text, int y, int font, uint16_t color);
    void drawCenteredText(const char* text, int y, int font);

    // SETTINGS под-экраны
    void drawSettingsMain();
    void drawSettingsConnInfo();
    void drawSettingsAbout();
    void drawSettingsRestartConfirm();

    // Boot — внутренние методы
    void _drawProgressBarFrame();       // рисует рамку один раз
    void _drawLogoStep(int step);       // рисует логотип с нужной яркостью

    // Вспомогательный метод для форматирования времени
    void formatTime(int totalSec, char* buffer, size_t bufsize);

    // Устаревшие — оставлены для совместимости, не используются
    void drawBootScreen();
    void updateProgressBar();
    void drawLogoWithColor(int fadeStep);
};

#endif