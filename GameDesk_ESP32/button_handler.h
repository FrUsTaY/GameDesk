// ====================================================================
// button_handler.h — обработчик кнопок GameDesk
// Версия: 1.1 (рабочая, на основе проверенного алгоритма)
// ====================================================================

#ifndef BUTTON_HANDLER_H
#define BUTTON_HANDLER_H

#include <Arduino.h>
#include "config.h"

enum class ButtonEvent : uint8_t {
    NONE = 0,
    LEFT,
    RIGHT,
    UP,
    DOWN,
    CENTER_SHORT,
    CENTER_LONG
};

class ButtonHandler {
public:
    ButtonHandler();
    void init();
    ButtonEvent processButtons();

private:
    static const int NUM_BUTTONS = 5;
    uint8_t _pins[NUM_BUTTONS];

    bool _lastStableState[NUM_BUTTONS];
    unsigned long _lastChangeTime[NUM_BUTTONS];

    // Для CENTER
    unsigned long _pressStartTime;
    bool _longPressTriggered;
};

#endif