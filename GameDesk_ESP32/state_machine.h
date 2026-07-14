// ====================================================================
// state_machine.h — конечный автомат UI устройства GameDesk
// Версия: 1.0
// Дата: 2026-06-18
// ====================================================================

#ifndef STATE_MACHINE_H
#define STATE_MACHINE_H

#include <Arduino.h>

// --------------------------------------------------------------------
// Перечисление всех состояний UI
// --------------------------------------------------------------------
enum class UIState : uint8_t {
    BOOT,           // загрузка
    HOME,           // главный экран (игра, таймер)
    MONITOR,        // мониторинг телеметрии
    STATS,          // общая статистика
    RECENT_GAMES,   // список последних игр
    DETAIL_VIEW,    // детальный просмотр игры
    SETTINGS,       // меню настроек
    OFFLINE,         // потеря связи с ПК
    WAITING         // ожидание запуска приложения на ПК (режим без связи)
};

// --------------------------------------------------------------------
// Класс StateMachine — управление переходами и обработка событий
// --------------------------------------------------------------------
class StateMachine {
public:
    // Конструктор: начальное состояние BOOT, lastActive = HOME
    StateMachine();

    // Геттеры
    UIState getState() const;
    UIState getLastActiveState() const;

    // Установка состояния (с проверкой и логированием)
    void setState(UIState newState);

    void onAppShutdown();   // вызывается при получении CMD=SHUTDOWN от ПК

    // Обработчики событий (вызываются из основного цикла)
    void onLeft();
    void onRight();
    void onUp();
    void onDown();
    void onCenterShort();
    void onCenterLong();

    // События от Serial
    void onSerialLost();
    void onSerialRestored();

private:
    UIState _currentState;      // текущее состояние
    UIState _lastActiveState;   // последнее активное состояние (не OFFLINE и не SETTINGS)

    // Вспомогательные методы для переключения по кольцу
    void switchLeft();          // переключить экран влево (по кольцу)
    void switchRight();         // переключить экран вправо (по кольцу)

    // Проверка, разрешена ли навигация в текущем состоянии
    bool isNavigationAllowed() const;
};

#endif // STATE_MACHINE_H