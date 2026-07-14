// ====================================================================
// display_manager.cpp — РАБОЧАЯ ВЕРСИЯ
// ====================================================================

#include "display_manager.h"
#include "config.h"
#include "serial_handler.h"

extern StateMachine ui;

DisplayManager::DisplayManager(TFT_eSPI& tft)
    : _tft(tft)
    , _lastState(UIState::BOOT)
    , _bootStartTime(0)
    , _lastProgressUpdate(0)
    , _fadeStep(-1)
    , _progress(0.0f)
    , _bootComplete(false)
    , _settingsSubState(MAIN_MENU)
    , _settingsSelectedIndex(0)
    , _connStatus{false, 1, 0}
    , _lastProgressFill(0)
    , _recentSelectedIndex(0)
    , _recentScrollOffset(0)
    , _lastGameName{0}
    , _lastTimerUpdate(0)
    , _isTimerActive(false)
{}

void DisplayManager::init() {
    _tft.init();
    _tft.setRotation(1);
    _tft.fillScreen(TFT_BLACK);
    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.setTextSize(1);
    pinMode(TFT_BL, OUTPUT);
    digitalWrite(TFT_BL, HIGH);
}

void DisplayManager::startBoot() {
    _bootStartTime = millis();
    _lastProgressUpdate = _bootStartTime;
    _fadeStep = -1;
    _progress = 0.0f;
    _bootComplete = false;
    _lastProgressFill = 0;
    _lastState = UIState::BOOT;

    _tft.fillScreen(TFT_BLACK);
    _drawProgressBarFrame();
    _drawLogoStep(0);
    _fadeStep = 0;
}

bool DisplayManager::updateBoot() {
    if (_bootComplete) return true;

    unsigned long now = millis();
    unsigned long elapsed = now - _bootStartTime;

    int newStep = (int)(elapsed / 500);
    if (newStep > 4) newStep = 4;
    if (newStep != _fadeStep) {
        _fadeStep = newStep;
        _drawLogoStep(_fadeStep);
    }

    const int BAR_FILL_WIDTH = 278;
    int targetFill = (int)((float)elapsed / 3000.0f * BAR_FILL_WIDTH);
    if (targetFill > BAR_FILL_WIDTH) targetFill = BAR_FILL_WIDTH;

    if (targetFill > _lastProgressFill) {
        _tft.fillRect(
            20 + 1 + _lastProgressFill,
            201,
            targetFill - _lastProgressFill,
            6,
            COLOR_RAM
        );
        _lastProgressFill = targetFill;
    }

    if (targetFill >= BAR_FILL_WIDTH && _fadeStep >= 4) {
        _bootComplete = true;
        return true;
    }
    return false;
}

void DisplayManager::_drawProgressBarFrame() {
    _tft.drawRect(20, 200, 280, 8, TFT_WHITE);
}

void DisplayManager::_drawLogoStep(int step) {
    const uint16_t colors[5] = {0x2104, 0x4208, 0x7BEF, 0xBDF7, 0xFFFF};
    uint16_t color = colors[step];

    _tft.setTextColor(color, TFT_BLACK);
    _tft.setTextFont(4);
    _tft.setTextSize(2);

    int cx = _tft.width() / 2;
    _tft.drawCentreString("GAME", cx, 55, 4);
    _tft.drawCentreString("DESK", cx, 115, 4);
}

void DisplayManager::drawBootScreen() {}
void DisplayManager::updateProgressBar() {}
void DisplayManager::drawLogoWithColor(int) {}

void DisplayManager::resetSettings() {
    _settingsSubState = MAIN_MENU;
    _settingsSelectedIndex = 0;
}

void DisplayManager::setConnectionStatus(const ConnectionInfo& status) {
    _connStatus = status;
}

bool DisplayManager::handleSettingsEvent(ButtonEvent event) {
    switch (event) {
        case ButtonEvent::UP:
            if (_settingsSubState == MAIN_MENU) {
                _settingsSelectedIndex--;
                if (_settingsSelectedIndex < 0) _settingsSelectedIndex = 3;
                drawSettings();
                return true;
            }
            break;

        case ButtonEvent::DOWN:
            if (_settingsSubState == MAIN_MENU) {
                _settingsSelectedIndex++;
                if (_settingsSelectedIndex > 3) _settingsSelectedIndex = 0;
                drawSettings();
                return true;
            }
            break;

        case ButtonEvent::LEFT:
        case ButtonEvent::RIGHT:
            if (_settingsSubState == RESTART_CONFIRM) {
                _settingsSubState = MAIN_MENU;
                drawSettings();
                return true;
            }
            return true;

        case ButtonEvent::CENTER_SHORT:
            if (_settingsSubState == MAIN_MENU) {
                switch (_settingsSelectedIndex) {
                    case 0: _settingsSubState = CONN_INFO;       drawSettings(); return true;
                    case 1: _settingsSubState = RESTART_CONFIRM; drawSettings(); return true;
                    case 2: _settingsSubState = ABOUT_INFO;      drawSettings(); return true;
                    case 3: ui.onCenterLong(); return true;
                }
            } else if (_settingsSubState == CONN_INFO || _settingsSubState == ABOUT_INFO) {
                _settingsSubState = MAIN_MENU;
                drawSettings();
                return true;
            } else if (_settingsSubState == RESTART_CONFIRM) {
                ESP.restart();
                return true;
            }
            break;

        default:
            break;
    }
    return false;
}

void DisplayManager::drawScreen(UIState state) {
    if (state == UIState::BOOT) return;

    if (state == UIState::SETTINGS && _lastState != UIState::SETTINGS) {
        resetSettings();
    }

    if (state == UIState::RECENT_GAMES && _lastState != UIState::RECENT_GAMES) {
        resetRecentGamesState();
    }

    if (state == _lastState) return;
    _lastState = state;

    switch (state) {
        case UIState::WAITING:       drawWaiting();      break;
        case UIState::HOME:          drawHome();         break;
        case UIState::MONITOR:       drawMonitor();      break;
        case UIState::STATS:         drawStats();        break;
        case UIState::RECENT_GAMES:  drawRecentGames();  break;
        case UIState::DETAIL_VIEW:   drawDetailView();   break;
        case UIState::SETTINGS:      drawSettings();     break;
        case UIState::OFFLINE:       drawOffline();      break;
        default: break;
    }
}

void DisplayManager::drawHeader(const char* title) {
    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.setTextFont(2);
    _tft.setTextSize(1);
    _tft.drawCentreString(title, _tft.width() / 2, 10, 2);
}

void DisplayManager::drawCenteredText(const char* text, int y, int font, uint16_t color) {
    _tft.setTextColor(color, COLOR_BG);
    _tft.setTextFont(font);
    _tft.setTextSize(1);
    _tft.drawCentreString(text, _tft.width() / 2, y, font);
}

void DisplayManager::drawCenteredText(const char* text, int y, int font) {
    drawCenteredText(text, y, font, COLOR_ACCENT);
}

void DisplayManager::formatTime(int totalSec, char* buffer, size_t bufsize) {
    int hours = totalSec / 3600;
    int minutes = (totalSec % 3600) / 60;
    snprintf(buffer, bufsize, "%02d:%02d", hours, minutes);
}

void DisplayManager::resetRecentGamesState() {
    _recentSelectedIndex = 0;
    _recentScrollOffset = 0;
}

void DisplayManager::recentGamesScrollUp() {
    if (gameCount == 0) return;
    if (_recentSelectedIndex > 0) {
        _recentSelectedIndex--;
        if (_recentSelectedIndex < _recentScrollOffset) {
            _recentScrollOffset = _recentSelectedIndex;
        }
        drawRecentGames();
    }
}

void DisplayManager::recentGamesScrollDown() {
    if (gameCount == 0) return;
    if (_recentSelectedIndex < gameCount - 1) {
        _recentSelectedIndex++;
        if (_recentSelectedIndex >= _recentScrollOffset + MAX_VISIBLE_ITEMS) {
            _recentScrollOffset = _recentSelectedIndex - MAX_VISIBLE_ITEMS + 1;
        }
        drawRecentGames();
    }
}

int DisplayManager::getRecentSelectedIndex() const {
    return _recentSelectedIndex;
}

void DisplayManager::drawRecentGames() {
    _tft.fillScreen(COLOR_BG);
    drawHeader("RECENT GAMES");

    const int lineHeight = 35;
    const int startY = 50;
    const int maxVisible = MAX_VISIBLE_ITEMS;

    if (gameCount == 0) {
        _tft.setTextColor(COLOR_TEXT, COLOR_BG);
        _tft.setTextFont(2);
        _tft.setTextSize(1);
        _tft.drawCentreString("Нет данных", _tft.width() / 2, startY + 60, 2);
        return;
    }

    int startIdx = _recentScrollOffset;
    int endIdx = startIdx + maxVisible;
    if (endIdx > gameCount) endIdx = gameCount;

    for (int i = startIdx; i < endIdx; i++) {
        int yPos = startY + (i - startIdx) * lineHeight;
        bool isSelected = (i == _recentSelectedIndex);

        uint16_t bgColor = isSelected ? COLOR_HIGHLIGHT : COLOR_BG;
        uint16_t textColor = isSelected ? COLOR_TEXT : TFT_DARKGREY;

        if (isSelected) {
            _tft.fillRect(10, yPos - 4, _tft.width() - 20, lineHeight - 4, bgColor);
        }

        char numBuf[8];
        snprintf(numBuf, sizeof(numBuf), "%d.", i + 1);
        _tft.setTextColor(textColor, bgColor);
        _tft.setTextFont(2);
        _tft.setTextSize(1);
        _tft.drawString(numBuf, 20, yPos);

        _tft.drawString(gameList[i].name, 60, yPos);

        char timeBuf[16];
        formatTime(gameList[i].total_sec, timeBuf, sizeof(timeBuf));
        int rightX = _tft.width() - 20;
        int textWidth = _tft.textWidth(timeBuf, 2);
        _tft.drawString(timeBuf, rightX - textWidth, yPos);
    }

    if (gameCount > maxVisible) {
        int barHeight = 80;
        int barY = startY + (maxVisible * lineHeight - barHeight) / 2;
        int barX = _tft.width() - 8;
        int barWidth = 4;

        float ratio = (float)maxVisible / gameCount;
        int thumbHeight = (int)(barHeight * ratio);
        if (thumbHeight < 10) thumbHeight = 10;

        float posRatio = (float)_recentScrollOffset / (gameCount - maxVisible);
        int thumbY = barY + (int)((barHeight - thumbHeight) * posRatio);

        _tft.fillRect(barX, barY, barWidth, barHeight, TFT_DARKGREY);
        _tft.fillRect(barX, thumbY, barWidth, thumbHeight, TFT_WHITE);
    }
}

void DisplayManager::drawHome() {
    _tft.fillScreen(COLOR_BG);

    _tft.setTextColor(TFT_DARKGREY, COLOR_BG);
    _tft.setTextFont(1);
    _tft.setTextSize(1);
    _tft.drawCentreString("GAMEDESK", _tft.width() / 2, 5, 1);

    bool hasGame = (strlen(parsedData.game) > 0 && strcmp(parsedData.game, "NONE") != 0);
    bool isIdle = (strcmp(parsedData.state, "IDLE") == 0);

    // ВАЖНО: этот экран рисуется только когда ПК УЖЕ подключён и шлёт данные
    // (иначе state machine была бы в OFFLINE/WAITING, см. drawOffline()/drawWaiting()).
    // Раньше здесь ошибочно показывался текст "Waiting for APP GameDesk / Launch
    // GameDesk.exe on PC" — то есть при живом соединении, но без активной игры,
    // на экране было написано "приложение не запущено", что вводит в заблуждение.
    // По ТЗ §8.1 в этом случае должно быть просто "Нет активной игры".
    if (isIdle && !hasGame) {
        _tft.setTextColor(TFT_DARKGREY, COLOR_BG);
        _tft.setTextFont(2);
        _tft.setTextSize(1);
        _tft.drawCentreString("Нет активной игры", _tft.width() / 2, 110, 2);
        _isTimerActive = false;
        _lastGameName[0] = '\0';
    }
    else if (hasGame) {
        _tft.setTextColor(COLOR_TEXT, COLOR_BG);
        _tft.setTextFont(4);
        _tft.setTextSize(1);
        _tft.drawCentreString(parsedData.game, _tft.width() / 2, 60, 4);
        strncpy(_lastGameName, parsedData.game, sizeof(_lastGameName) - 1);
        _lastGameName[sizeof(_lastGameName) - 1] = '\0';
        _isTimerActive = true;

        _tft.setTextColor(COLOR_ACCENT, COLOR_BG);
        _tft.setTextFont(4);
        _tft.setTextSize(1);
        if (strlen(parsedData.session) > 0 && strcmp(parsedData.session, "00:00:00") != 0) {
            _tft.drawCentreString(parsedData.session, _tft.width() / 2, 130, 4);
        } else {
            _tft.drawCentreString("00:00:00", _tft.width() / 2, 130, 4);
        }
        _lastTimerUpdate = millis();
    }
    else {
        _tft.setTextColor(TFT_DARKGREY, COLOR_BG);
        _tft.setTextFont(2);
        _tft.setTextSize(1);
        _tft.drawCentreString("No active game", _tft.width() / 2, 80, 2);
        _lastGameName[0] = '\0';
        _isTimerActive = false;
    }

    _tft.setTextColor(TFT_DARKGREY, COLOR_BG);
    _tft.setTextFont(1);
    _tft.setTextSize(1);
    _tft.drawCentreString("← MON | STA | REC →", _tft.width() / 2, _tft.height() - 15, 1);
}

void DisplayManager::drawMonitor() {
    _tft.fillScreen(COLOR_BG);
    drawHeader("MONITOR");

    // Реальные данные из последнего DATA-пакета (parsedData), а не заглушка.
    // -1 (нет данных с ПК, например LibreHardwareMonitor недоступен) -> "--"
    char buf[24];

    if (parsedData.cpu >= 0) {
        snprintf(buf, sizeof(buf), "CPU: %dC", parsedData.cpu);
    } else {
        snprintf(buf, sizeof(buf), "CPU: --");
    }
    drawCenteredText(buf, 100, 4, COLOR_CPU);

    if (parsedData.gpu >= 0) {
        snprintf(buf, sizeof(buf), "GPU: %dC", parsedData.gpu);
    } else {
        snprintf(buf, sizeof(buf), "GPU: --");
    }
    drawCenteredText(buf, 140, 4, COLOR_GPU);

    if (parsedData.ram >= 0) {
        snprintf(buf, sizeof(buf), "RAM: %d%%", parsedData.ram);
    } else {
        snprintf(buf, sizeof(buf), "RAM: --");
    }
    drawCenteredText(buf, 180, 4, COLOR_RAM);
}

void DisplayManager::drawStats() {
    _tft.fillScreen(COLOR_BG);
    drawHeader("STATS");

    // Реальные данные из последнего <STATS;...> пакета, а не заглушка.
    // ESP32 сам ничего не считает (ТЗ §0) — просто отображает то, что прислал ПК.
    if (!statsSummary.hasData) {
        drawCenteredText("No data yet", 130, 2, TFT_DARKGREY);
        return;
    }

    char buf[24];
    char timeBuf[8];

    if (statsSummary.weekly_sec >= 0) {
        formatTime(statsSummary.weekly_sec, timeBuf, sizeof(timeBuf));
        snprintf(buf, sizeof(buf), "Week: %s", timeBuf);
    } else {
        snprintf(buf, sizeof(buf), "Week: --");
    }
    drawCenteredText(buf, 100, 4);

    if (statsSummary.monthly_sec >= 0) {
        formatTime(statsSummary.monthly_sec, timeBuf, sizeof(timeBuf));
        snprintf(buf, sizeof(buf), "Month: %s", timeBuf);
    } else {
        snprintf(buf, sizeof(buf), "Month: --");
    }
    drawCenteredText(buf, 140, 4);

    if (statsSummary.totalGames >= 0) {
        snprintf(buf, sizeof(buf), "Games: %d", statsSummary.totalGames);
    } else {
        snprintf(buf, sizeof(buf), "Games: --");
    }
    drawCenteredText(buf, 180, 4, COLOR_TEXT);
}

void DisplayManager::updateHomeTimer() {
    if (_lastState != UIState::HOME) return;
    if (!_isTimerActive) return;

    unsigned long now = millis();
    if (now - _lastTimerUpdate < 1000) return;

    _lastTimerUpdate = now;

    int timerX = 0;
    int timerY = 120;
    int timerW = _tft.width();
    int timerH = 50;

    _tft.fillRect(timerX, timerY, timerW, timerH, COLOR_BG);

    _tft.setTextColor(COLOR_ACCENT, COLOR_BG);
    _tft.setTextFont(4);
    _tft.setTextSize(1);
    if (strlen(parsedData.session) > 0 && strcmp(parsedData.session, "00:00:00") != 0) {
        _tft.drawCentreString(parsedData.session, _tft.width() / 2, timerY, 4);
    } else {
        _tft.drawCentreString("00:00:00", _tft.width() / 2, timerY, 4);
    }
}

void DisplayManager::drawDetailView() {
    if (gameCount == 0 || _recentSelectedIndex < 0 || _recentSelectedIndex >= gameCount) {
        _tft.fillScreen(COLOR_BG);
        drawHeader("DETAIL VIEW");
        _tft.setTextColor(TFT_DARKGREY, COLOR_BG);
        _tft.setTextFont(2);
        _tft.setTextSize(1);
        _tft.drawCentreString("Нет данных", _tft.width() / 2, 120, 2);
        return;
    }

    const GameEntry& game = gameList[_recentSelectedIndex];
    _tft.fillScreen(COLOR_BG);

    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.setTextFont(4);
    _tft.setTextSize(1);
    _tft.drawCentreString(game.name, _tft.width() / 2, 30, 4);

    int lineY = 70;
    _tft.drawLine(20, lineY, _tft.width() - 20, lineY, TFT_DARKGREY);

    const int startY = 90;
    const int lineHeight = 35;
    int y = startY;

    auto formatTimeStr = [&](int seconds) -> String {
        if (seconds < 0) return "--";
        int hours = seconds / 3600;
        int minutes = (seconds % 3600) / 60;
        char buf[16];
        snprintf(buf, sizeof(buf), "%02d:%02d", hours, minutes);
        return String(buf);
    };

    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.setTextFont(2);
    _tft.setTextSize(1);
    _tft.drawString("Total:", 30, y);
    String totalStr = formatTimeStr(game.total_sec);
    _tft.setTextColor(COLOR_ACCENT, COLOR_BG);
    _tft.drawString(totalStr, 120, y);
    y += lineHeight;

    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.drawString("Week:", 30, y);
    String weekStr = formatTimeStr(game.weekly_sec);
    _tft.setTextColor(COLOR_GPU, COLOR_BG);
    _tft.drawString(weekStr, 120, y);
    y += lineHeight;

    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.drawString("Month:", 30, y);
    String monthStr = formatTimeStr(game.monthly_sec);
    _tft.setTextColor(COLOR_RAM, COLOR_BG);
    _tft.drawString(monthStr, 120, y);
    y += lineHeight;

    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.drawString("Last:", 30, y);
    String lastStr = (strlen(game.last_played) > 0) ? String(game.last_played) : "--";
    _tft.setTextColor(TFT_DARKGREY, COLOR_BG);
    _tft.drawString(lastStr, 120, y);

    int hintY = _tft.height() - 30;
    _tft.setTextColor(TFT_DARKGREY, COLOR_BG);
    _tft.setTextFont(1);
    _tft.setTextSize(1);
    _tft.drawCentreString("← назад   (CENTER долгое=настройки)", _tft.width() / 2, hintY, 1);
}

void DisplayManager::drawSettings() {
    switch (_settingsSubState) {
        case MAIN_MENU:       drawSettingsMain();          break;
        case CONN_INFO:       drawSettingsConnInfo();      break;
        case ABOUT_INFO:      drawSettingsAbout();         break;
        case RESTART_CONFIRM: drawSettingsRestartConfirm();break;
    }
}

void DisplayManager::drawSettingsMain() {
    _tft.fillScreen(COLOR_BG);
    drawHeader("SETTINGS");
    const char* items[] = {"Connection Status", "Restart Device", "About", "Exit"};
    for (int i = 0; i < 4; i++) {
        uint16_t textColor = (i == _settingsSelectedIndex) ? TFT_RED : COLOR_TEXT;
        _tft.setTextColor(textColor, COLOR_BG);
        _tft.setTextFont(2);
        _tft.setTextSize(1);
        _tft.drawCentreString(items[i], _tft.width() / 2, 80 + i * 35, 2);
    }
}

void DisplayManager::drawSettingsConnInfo() {
    _tft.fillScreen(COLOR_BG);
    drawHeader("Connection Status");
    char buf[40];
    // _connStatus теперь реально обновляется каждую итерацию loop() из
    // getConnectionInfo() (см. GameDesk_ESP32.ino) -- раньше setConnectionStatus()
    // нигде не вызывался, поэтому здесь всегда были нули/false.
    unsigned long lastPacketSec = (millis() - _connStatus.lastPacketMs) / 1000;
    unsigned long uptimeSec = millis() / 1000;
    int y = 70;
    _tft.setTextFont(2);
    _tft.setTextSize(1);
    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.drawCentreString("Device: GameDesk", _tft.width() / 2, y, 2); y += 30;
    _tft.drawCentreString(_connStatus.connected ? "Connected" : "Offline", _tft.width() / 2, y, 2); y += 30;
    sprintf(buf, "VER: %d", _connStatus.ver);
    _tft.drawCentreString(buf, _tft.width() / 2, y, 2); y += 30;
    sprintf(buf, "Last: %lu sec ago", lastPacketSec);
    _tft.drawCentreString(buf, _tft.width() / 2, y, 2); y += 30;
    sprintf(buf, "Uptime: %lu sec", uptimeSec);
    _tft.drawCentreString(buf, _tft.width() / 2, y, 2);
    _tft.setTextColor(COLOR_ACCENT, COLOR_BG);
    _tft.setTextFont(1);
    _tft.drawCentreString("CENTER = back", _tft.width() / 2, 220, 1);
}

void DisplayManager::drawSettingsAbout() {
    _tft.fillScreen(COLOR_BG);
    drawHeader("About");
    int y = 70;
    _tft.setTextFont(2);
    _tft.setTextSize(1);
    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.drawCentreString("GameDesk v1.0", _tft.width() / 2, y, 2); y += 30;
    _tft.drawCentreString("FW: 1.0", _tft.width() / 2, y, 2); y += 30;
    _tft.drawCentreString("ESP32-32S NodeMCU", _tft.width() / 2, y, 2); y += 30;
    _tft.drawCentreString("Display: ST7789V 320x240", _tft.width() / 2, y, 2);
    _tft.setTextColor(COLOR_ACCENT, COLOR_BG);
    _tft.setTextFont(1);
    _tft.drawCentreString("CENTER = back", _tft.width() / 2, 220, 1);
}

void DisplayManager::drawSettingsRestartConfirm() {
    _tft.fillScreen(COLOR_BG);
    drawHeader("Restart Device");
    _tft.setTextFont(2);
    _tft.setTextSize(1);
    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.drawCentreString("Restart device?", _tft.width() / 2, 90, 2);
    _tft.setTextColor(COLOR_ACCENT, COLOR_BG);
    _tft.drawCentreString("Yes      /      No", _tft.width() / 2, 140, 2);
    _tft.setTextColor(COLOR_TEXT, COLOR_BG);
    _tft.setTextFont(1);
    _tft.drawCentreString("CENTER = Yes   LEFT/RIGHT = No", _tft.width() / 2, 190, 1);
}

void DisplayManager::drawOffline() {
    _tft.fillScreen(TFT_BLACK);
    _tft.setTextColor(TFT_RED, TFT_BLACK);
    _tft.setTextFont(4);
    _tft.setTextSize(1);
    _tft.drawCentreString("Waiting for APP GameDesk", _tft.width() / 2, 90, 4);
    _tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
    _tft.setTextFont(2);
    _tft.drawCentreString("Launch GameDesk.exe on PC", _tft.width() / 2, 150, 2);
}

void DisplayManager::drawWaiting() {
    _tft.fillScreen(TFT_BLACK);
    _tft.setTextColor(TFT_RED, TFT_BLACK);
    _tft.setTextFont(4);
    _tft.setTextSize(1);
    _tft.drawCentreString("Waiting for APP GameDesk", _tft.width() / 2, 90, 4);
    _tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
    _tft.setTextFont(2);
    _tft.drawCentreString("Launch GameDesk.exe on PC", _tft.width() / 2, 150, 2);
}

void DisplayManager::refreshScreen() {
    UIState state = _lastState;
    switch (state) {
        case UIState::HOME:          drawHome();         break;
        case UIState::MONITOR:       drawMonitor();      break;
        case UIState::STATS:         drawStats();        break;
        case UIState::RECENT_GAMES:  drawRecentGames();  break;
        case UIState::DETAIL_VIEW:   drawDetailView();   break;
        case UIState::SETTINGS:      drawSettings();     break;
        case UIState::OFFLINE:       drawOffline();      break;
        case UIState::WAITING:       drawWaiting();      break;
        default: break;
    }
}