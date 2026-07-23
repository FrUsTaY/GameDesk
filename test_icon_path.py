import os
import sys

def get_icon_path():
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    icon_path = os.path.join(base_path, 'icon.ico')
    if os.path.exists(icon_path):
        return icon_path

    # Check parent dir (if run from inside a submodule)
    icon_path = os.path.join(os.path.dirname(base_path), 'icon.ico')
    if os.path.exists(icon_path):
        return icon_path

    # Check current working dir
    icon_path = os.path.join(os.getcwd(), 'icon.ico')
    if os.path.exists(icon_path):
        return icon_path

    return None

print(get_icon_path())
