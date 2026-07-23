import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import config

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, stats_manager, on_close_callback):
        super().__init__(parent)
        self.title("Управление играми - GameDesk")
        self.geometry("600x400")
        self.stats_manager = stats_manager
        self.on_close_callback = on_close_callback

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Main frame
        self.main_frame = ttk.Frame(self, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview (Game List)
        columns = ("exe_name", "display_name", "total_time")
        self.tree = ttk.Treeview(self.main_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("exe_name", text="Исполняемый файл (EXE)")
        self.tree.heading("display_name", text="Название игры")
        self.tree.heading("total_time", text="Сыграно (часов)")

        self.tree.column("exe_name", width=150)
        self.tree.column("display_name", width=250)
        self.tree.column("total_time", width=100, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Buttons frame
        self.btn_frame = ttk.Frame(self.main_frame)
        self.btn_frame.pack(fill=tk.X)

        self.add_btn = ttk.Button(self.btn_frame, text="Добавить", command=self.add_game)
        self.add_btn.pack(side=tk.LEFT, padx=5)

        self.edit_btn = ttk.Button(self.btn_frame, text="Изменить", command=self.edit_game)
        self.edit_btn.pack(side=tk.LEFT, padx=5)

        self.del_btn = ttk.Button(self.btn_frame, text="Удалить", command=self.delete_game)
        self.del_btn.pack(side=tk.LEFT, padx=5)

        self.refresh_list()

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        games_dict = config.load_games()
        for exe, display_name in games_dict.items():
            stats = self.stats_manager.get_game_stats(display_name)
            total_time_str = "0.0"
            if stats:
                total_time_hours = stats.get("total_time", 0) / 3600
                total_time_str = f"{total_time_hours:.1f}"

            self.tree.insert("", tk.END, values=(exe, display_name, total_time_str))

    def _save_changes(self, new_dict):
        try:
            with open(config.GAMES_LIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_dict, f, ensure_ascii=False, indent=4)
            config.GAMES = new_dict
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

    def add_game(self):
        self._open_edit_dialog("Добавить игру")

    def edit_game(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите игру для изменения")
            return
        item_values = self.tree.item(selected[0], "values")
        self._open_edit_dialog("Изменить игру", item_values[0], item_values[1])

    def _open_edit_dialog(self, title, initial_exe="", initial_name=""):
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.geometry("400x150")
        dlg.grab_set()

        ttk.Label(dlg, text="Исполняемый файл (например, hl2.exe):").pack(pady=(10, 0))
        exe_var = tk.StringVar(value=initial_exe)
        exe_entry = ttk.Entry(dlg, textvariable=exe_var, width=50)
        exe_entry.pack(pady=5)

        ttk.Label(dlg, text="Название игры (отображаемое):").pack()
        name_var = tk.StringVar(value=initial_name)
        name_entry = ttk.Entry(dlg, textvariable=name_var, width=50)
        name_entry.pack(pady=5)

        def save():
            exe = exe_var.get().strip().lower()
            name = name_var.get().strip()

            if not exe or not name:
                messagebox.showerror("Ошибка", "Оба поля должны быть заполнены", parent=dlg)
                return

            games_dict = config.load_games()

            if initial_exe and initial_exe != exe:
                if exe in games_dict:
                    messagebox.showerror("Ошибка", "Такой EXE уже существует", parent=dlg)
                    return
                del games_dict[initial_exe]
            elif not initial_exe and exe in games_dict:
                 messagebox.showerror("Ошибка", "Такой EXE уже существует", parent=dlg)
                 return

            games_dict[exe] = name
            self._save_changes(games_dict)
            dlg.destroy()

        ttk.Button(dlg, text="Сохранить", command=save).pack(pady=10)

    def delete_game(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите игру для удаления")
            return

        item_values = self.tree.item(selected[0], "values")
        exe_name = item_values[0]

        if messagebox.askyesno("Подтверждение", f"Удалить {exe_name} из списка отслеживаемых игр?"):
            games_dict = config.load_games()
            if exe_name in games_dict:
                del games_dict[exe_name]
                self._save_changes(games_dict)

    def on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()
