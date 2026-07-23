import sys
import os

try:
    import winreg
except ImportError:
    winreg = None

APP_NAME = "GameDesk"

def get_exe_path():
    """Возвращает путь к исполняемому файлу (.exe) или скрипту."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        return os.path.abspath(sys.argv[0])

def is_autostart_enabled() -> bool:
    """Проверяет, включен ли автозапуск в реестре."""
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return value == get_exe_path()
    except OSError:
        return False

def set_autostart(enable: bool) -> bool:
    """Включает или выключает автозапуск."""
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        if enable:
            # Wrap in quotes to safely handle paths with spaces in the Windows Registry
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{get_exe_path()}"')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except OSError:
                pass # Уже удалено
        winreg.CloseKey(key)
        return True
    except OSError as e:
        print(f"[ERROR] Failed to set autostart: {e}")
        return False
