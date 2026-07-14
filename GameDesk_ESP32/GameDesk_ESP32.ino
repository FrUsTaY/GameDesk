// ====================================================================
// GameDesk_ESP32.ino — РАБОЧАЯ ВЕРСИЯ
// ====================================================================

#include <TFT_eSPI.h>
#include "config.h"
#include "state_machine.h"
#include "display_manager.h"
#include "button_handler.h"
#include "serial_handler.h"

TFT_eSPI tft = TFT_eSPI();
DisplayManager display(tft);
StateMachine ui;
ButtonHandler buttons;

bool debugMode = false;

void onSerialLost() {
    ui.onSerialLost();
}

void onSerialRestored() {
    ui.onSerialRestored();
}

void onAppShutdown() {
    ui.onAppShutdown();
    resetOfflineTimer();
    Serial.println("[APP] Shutdown received, entering WAITING");
}

void setup() {
    Serial.begin(SERIAL_BAUD);
    Serial.println(F("GameDesk v1.0 starting..."));

    display.init();
    buttons.init();
    serialHandlerInit();

    ui.setState(UIState::BOOT);
    display.startBoot();
}

void loop() {
    unsigned long now = millis();

    if (ui.getState() == UIState::BOOT) {
        static unsigned long bootStart = millis();
        if (now - bootStart < 2000) {
            static unsigned long lastCheck = 0;
            if (now - lastCheck >= 50) {
                lastCheck = now;
                if (digitalRead(BTN_CENTER) == LOW) {
                    debugMode = true;
                    Serial.println("=== DEBUG MODE ACTIVATED ===");
                }
            }
        }

        if (display.updateBoot()) {
            ui.setState(UIState::HOME);
            display.drawScreen(ui.getState());
            if (debugMode) {
                Serial.println("[DBG] Boot complete, switching to HOME");
            }
        }
        return;
    }

    serialHandlerUpdate();

    // Синхронизируем статус соединения с экраном SETTINGS -> Connection Status.
    // Раньше этого вызова не было вообще, поэтому DisplayManager всегда видел
    // {connected=false, ver=1, lastPacketMs=0} — отсюда вечный "Offline".
    display.setConnectionStatus(getConnectionInfo());

    if (parsedData.hasNewList && ui.getState() == UIState::RECENT_GAMES) {
        display.drawRecentGames();
        clearSerialDataFlag();
    }

    ButtonEvent event = buttons.processButtons();

    if (debugMode && event != ButtonEvent::NONE) {
        Serial.print("[DBG] Event: ");
        Serial.println((int)event);
    }

    bool eventHandled = false;

    if (ui.getState() == UIState::SETTINGS) {
        if (event != ButtonEvent::CENTER_LONG) {
            eventHandled = display.handleSettingsEvent(event);
        }
        if (eventHandled) {
            display.drawScreen(ui.getState());
            delay(1);
            return;
        }
    }

    if (ui.getState() == UIState::RECENT_GAMES) {
        if (event == ButtonEvent::UP) {
            display.recentGamesScrollUp();
            eventHandled = true;
        } else if (event == ButtonEvent::DOWN) {
            display.recentGamesScrollDown();
            eventHandled = true;
        }
    }

    if (!eventHandled) {
        switch (event) {
            case ButtonEvent::LEFT:          ui.onLeft();          break;
            case ButtonEvent::RIGHT:         ui.onRight();         break;
            case ButtonEvent::UP:            ui.onUp();            break;
            case ButtonEvent::DOWN:          ui.onDown();          break;
            case ButtonEvent::CENTER_SHORT:  ui.onCenterShort();   break;
            case ButtonEvent::CENTER_LONG:   ui.onCenterLong();    break;
            default: break;
        }
    }

    display.drawScreen(ui.getState());

    if (ui.getState() == UIState::HOME) {
        display.updateHomeTimer();
    }

    if (isSerialDataAvailable()) {
        UIState state = ui.getState();
        if (state != UIState::SETTINGS && state != UIState::OFFLINE && state != UIState::BOOT && state != UIState::WAITING) {
            display.refreshScreen();
        }
        clearSerialDataFlag();
    }

    delay(1);
}