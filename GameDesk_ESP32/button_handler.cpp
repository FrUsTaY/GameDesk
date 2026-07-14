// ====================================================================
// button_handler.cpp — реализация обработчика кнопок
// Версия: 1.1 (рабочая, на основе проверенного алгоритма)
// ====================================================================

#include "button_handler.h"

ButtonHandler::ButtonHandler()
    : _pressStartTime(0)
    , _longPressTriggered(false)
{
    _pins[0] = BTN_LEFT;
    _pins[1] = BTN_RIGHT;
    _pins[2] = BTN_UP;
    _pins[3] = BTN_DOWN;
    _pins[4] = BTN_CENTER;
}

void ButtonHandler::init() {
    for (int i = 0; i < NUM_BUTTONS; i++) {
        pinMode(_pins[i], INPUT_PULLUP);
        _lastStableState[i] = digitalRead(_pins[i]);
        _lastChangeTime[i] = millis();
    }
    _pressStartTime = 0;
    _longPressTriggered = false;
}

ButtonEvent ButtonHandler::processButtons() {
    unsigned long now = millis();

    for (int i = 0; i < NUM_BUTTONS; i++) {
        bool current = digitalRead(_pins[i]);

        // ---- Антидребезг (как в проверенном алгоритме) ----
        if (current != _lastStableState[i]) {
            if (now - _lastChangeTime[i] > BTN_DEBOUNCE_MS) {
                _lastStableState[i] = current;
                _lastChangeTime[i] = now;

                if (current == LOW) {
                    // Нажатие
                    if (i == 4) { // CENTER
                        _pressStartTime = now;
                        _longPressTriggered = false;
                        // Не возвращаем событие, ждём отпускания или долгого удержания
                    } else {
                        // LEFT/RIGHT/UP/DOWN
                        return static_cast<ButtonEvent>(i + 1);
                    }
                } else {
                    // Отпускание
                    if (i == 4) { // CENTER
                        if (!_longPressTriggered) {
                            unsigned long duration = now - _pressStartTime;
                            if (duration < BTN_SHORT_MAX_MS) {
                                return ButtonEvent::CENTER_SHORT;
                            } else if (duration >= BTN_LONG_MS) {
                                return ButtonEvent::CENTER_LONG;
                            }
                            // между порогами — ничего не возвращаем
                        }
                    }
                }
            }
        } else {
            // Если состояние не изменилось, но это CENTER и оно нажато — проверяем долгое удержание
            if (i == 4 && _lastStableState[4] == LOW && !_longPressTriggered) {
                unsigned long holdTime = now - _pressStartTime;
                if (holdTime >= BTN_LONG_MS) {
                    _longPressTriggered = true;
                    return ButtonEvent::CENTER_LONG;
                }
            }
        }
    }

    return ButtonEvent::NONE;
}