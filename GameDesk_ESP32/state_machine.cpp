// ====================================================================
// state_machine.cpp — РАБОЧАЯ ВЕРСИЯ
// ====================================================================

#include "state_machine.h"

static const char* stateToString(UIState state) {
    switch (state) {
        case UIState::BOOT:          return "BOOT";
        case UIState::HOME:          return "HOME";
        case UIState::MONITOR:       return "MONITOR";
        case UIState::STATS:         return "STATS";
        case UIState::RECENT_GAMES:  return "RECENT_GAMES";
        case UIState::DETAIL_VIEW:   return "DETAIL_VIEW";
        case UIState::SETTINGS:      return "SETTINGS";
        case UIState::OFFLINE:       return "OFFLINE";
        case UIState::WAITING:       return "WAITING";
        default:                     return "UNKNOWN";
    }
}

StateMachine::StateMachine()
    : _currentState(UIState::BOOT)
    , _lastActiveState(UIState::HOME)
{
    Serial.print("[STATE] → ");
    Serial.println(stateToString(_currentState));
}

UIState StateMachine::getState() const {
    return _currentState;
}

UIState StateMachine::getLastActiveState() const {
    return _lastActiveState;
}

void StateMachine::setState(UIState newState) {
    if (_currentState == newState) return;

    UIState prevState = _currentState;

    if (newState != UIState::OFFLINE && newState != UIState::SETTINGS) {
        _lastActiveState = newState;
    }

    _currentState = newState;

    Serial.print("[STATE] ");
    Serial.print(stateToString(prevState));
    Serial.print(" → ");
    Serial.println(stateToString(newState));
}

bool StateMachine::isNavigationAllowed() const {
    if (_currentState == UIState::OFFLINE || _currentState == UIState::SETTINGS) {
        return false;
    }
    if (_currentState == UIState::DETAIL_VIEW) {
        return false;
    }
    return true;
}

void StateMachine::switchLeft() {
    if (!isNavigationAllowed()) return;

    UIState newState = _currentState;
    switch (_currentState) {
        case UIState::HOME:          newState = UIState::RECENT_GAMES; break;
        case UIState::RECENT_GAMES:  newState = UIState::STATS;        break;
        case UIState::STATS:         newState = UIState::MONITOR;      break;
        case UIState::MONITOR:       newState = UIState::HOME;         break;
        default: return;
    }
    setState(newState);
}

void StateMachine::switchRight() {
    if (!isNavigationAllowed()) return;

    UIState newState = _currentState;
    switch (_currentState) {
        case UIState::HOME:          newState = UIState::MONITOR;      break;
        case UIState::MONITOR:       newState = UIState::STATS;        break;
        case UIState::STATS:         newState = UIState::RECENT_GAMES; break;
        case UIState::RECENT_GAMES:  newState = UIState::HOME;         break;
        default: return;
    }
    setState(newState);
}

void StateMachine::onLeft() {
    if (_currentState == UIState::DETAIL_VIEW) {
        setState(UIState::RECENT_GAMES);
        return;
    }
    switchLeft();
}

void StateMachine::onRight() {
    if (_currentState == UIState::DETAIL_VIEW) {
        return;
    }
    switchRight();
}

void StateMachine::onUp() {}
void StateMachine::onDown() {}

void StateMachine::onCenterShort() {
    if (_currentState == UIState::RECENT_GAMES) {
        setState(UIState::DETAIL_VIEW);
    }
}

void StateMachine::onCenterLong() {
    if (_currentState == UIState::BOOT || _currentState == UIState::OFFLINE) {
        return;
    }

    if (_currentState == UIState::SETTINGS) {
        UIState target = _lastActiveState;
        if (target == UIState::SETTINGS || target == UIState::OFFLINE || target == UIState::BOOT) {
            target = UIState::HOME;
        }
        setState(target);
        return;
    }

    setState(UIState::SETTINGS);
}

void StateMachine::onSerialLost() {
    if (_currentState == UIState::OFFLINE) return;
    setState(UIState::OFFLINE);
}

void StateMachine::onSerialRestored() {
    if (_currentState != UIState::OFFLINE) return;
    UIState target = _lastActiveState;
    if (target == UIState::SETTINGS || target == UIState::OFFLINE || target == UIState::BOOT) {
        target = UIState::HOME;
    }
    setState(target);
}

void StateMachine::onAppShutdown() {
    if (_currentState == UIState::WAITING || _currentState == UIState::OFFLINE) {
        return;
    }
    setState(UIState::WAITING);
}