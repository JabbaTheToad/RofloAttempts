import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from config import Config


class ChecklistTab:
    """Класс для вкладки с чек-листом"""

    def __init__(self, parent, tab_name, items, app):
        self.parent = parent
        self.tab_name = tab_name
        self.items = items
        self.app = app
        self.checklist_items = {}
        self.selection_vars = {}  # Переменные для чекбоксов выбора

        self.frame = ttk.Frame(parent)
        self.setup_ui()

    def setup_ui(self):
        """Создает интерфейс вкладки"""
        # Canvas с прокруткой
        canvas_frame = ttk.Frame(self.frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(canvas_frame, height=Config.CANVAS_HEIGHT)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", configure_scroll_region)

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Создаем пункты
        for i, item in enumerate(self.items):
            self.create_item(scrollable_frame, item, i)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_item(self, parent, item, row):
        """Создает отдельный пункт с чекбоксом для выбора справа"""
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, sticky=tk.EW, pady=2)
        frame.columnconfigure(1, weight=1)  # Растягиваем текст

        # Переменная для статуса (0 - нет, 1 - done, 2 - bug)
        status_var = tk.IntVar()

        # Переменная для выбора пункта (чекбокс справа)
        select_var = tk.BooleanVar()
        self.selection_vars[item] = select_var

        self.checklist_items[item] = {
            "var": status_var,
            "comment": None,
            "frame": frame,
            "select_var": select_var
        }

        # Кнопка для отметки статуса (слева)
        status_btn = tk.Button(frame, text="⚪", width=3, relief=tk.FLAT,
                               command=lambda i=item: self.show_status_dialog(i))
        status_btn.grid(row=0, column=0, padx=(0, 5))

        # Текст пункта (по центру, растягивается)
        text_label = ttk.Label(frame, text=item, anchor=tk.W)
        text_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        # Метка для комментария
        comment_label = ttk.Label(frame, text="", foreground="red", font=('Arial', 9, 'italic'))
        comment_label.grid(row=0, column=2, sticky=tk.W, padx=5)

        # Чекбокс для выбора пункта (справа)
        select_cb = ttk.Checkbutton(frame, variable=select_var,
                                    command=self.on_selection_change)
        select_cb.grid(row=0, column=3, padx=(5, 0))

        self.checklist_items[item]["btn"] = status_btn
        self.checklist_items[item]["text_label"] = text_label
        self.checklist_items[item]["comment_label"] = comment_label
        self.checklist_items[item]["select_cb"] = select_cb

    def on_selection_change(self):
        """Обработчик изменения выделения"""
        self.app.update_bulk_buttons()

    def get_selected_items(self):
        """Возвращает список выбранных пунктов"""
        return [item for item, var in self.selection_vars.items() if var.get()]

    def center_window(self, window):
        """Центрирует окно относительно главного окна"""
        window.update_idletasks()

        main_x = self.app.root.winfo_x()
        main_y = self.app.root.winfo_y()
        main_width = self.app.root.winfo_width()
        main_height = self.app.root.winfo_height()

        window_width = window.winfo_width()
        window_height = window.winfo_height()

        x = main_x + (main_width // 2) - (window_width // 2)
        y = main_y + (main_height // 2) - (window_height // 2)

        window.geometry(f"+{x}+{y}")

    def show_status_dialog(self, item):
        """Показывает диалог выбора статуса"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Выберите статус")
        dialog.geometry("300x150")
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.focus_set()

        self.center_window(dialog)

        dialog.lift()
        dialog.attributes('-topmost', True)
        dialog.after(100, lambda: dialog.attributes('-topmost', False))

        ttk.Label(dialog, text=f"Пункт: {item}", wraplength=280).pack(pady=10)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        def set_done():
            self.set_item_status(item, 1, None)
            dialog.destroy()

        def set_bug():
            dialog.destroy()
            self.show_comment_dialog(item)

        def set_none():
            self.set_item_status(item, 0, None)
            dialog.destroy()

        tk.Button(btn_frame, text="✓ Done", bg=Config.COLORS["done"],
                  fg="white", width=10, command=set_done).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="⚠ BUG", bg=Config.COLORS["bug"],
                  fg="white", width=10, command=set_bug).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✕ Сброс", bg="gray",
                  fg="white", width=10, command=set_none).pack(side=tk.LEFT, padx=5)

    def show_comment_dialog(self, item):
        """Показывает диалог ввода комментария"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Комментарий")
        dialog.geometry("400x150")
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.focus_set()

        self.center_window(dialog)

        dialog.lift()
        dialog.attributes('-topmost', True)
        dialog.after(100, lambda: dialog.attributes('-topmost', False))

        ttk.Label(dialog, text=f"Опишите баг для: {item}", wraplength=380).pack(pady=10)

        comment_entry = ttk.Entry(dialog, width=50)
        comment_entry.pack(pady=5)
        comment_entry.focus_set()

        def save_comment():
            comment = comment_entry.get().strip()
            self.set_item_status(item, 2, comment if comment else "")
            dialog.destroy()

        def cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Сохранить", command=save_comment).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=5)

        comment_entry.bind('<Return>', lambda e: save_comment())
        comment_entry.bind('<Escape>', lambda e: cancel())

    def set_item_status(self, item, status, comment):
        """Устанавливает статус пункта"""
        data = self.checklist_items[item]
        data["var"].set(status)
        data["comment"] = comment

        btn = data["btn"]
        comment_label = data["comment_label"]

        if status == 1:  # Done
            btn.config(text="✓", bg=Config.COLORS["done"])
            comment_label.config(text="")
        elif status == 2:  # Bug
            btn.config(text="⚠", bg=Config.COLORS["bug"])
            if comment:
                comment_label.config(text=f"💬 {comment[:30]}...")
        else:  # None
            btn.config(text="⚪", bg="SystemButtonFace")
            comment_label.config(text="")

        # Сохраняем в модель
        self.app.save_item_status(self.tab_name, item, status, comment)

    def get_item_status(self, item):
        """Возвращает статус пункта"""
        return self.checklist_items[item]["var"].get()

    def mark_selected_done(self):
        """Помечает выбранные пункты как Done"""
        selected = self.get_selected_items()
        if selected:
            for item in selected:
                self.set_item_status(item, 1, None)
                # Снимаем выделение
                self.selection_vars[item].set(False)
            self.app.update_bulk_buttons()

    def mark_selected_bug(self):
        """Помечает выбранные пункты как BUG"""
        selected = self.get_selected_items()
        if selected:
            # Показываем диалог для комментария
            dialog = tk.Toplevel(self.app.root)
            dialog.title("Комментарий для выбранных пунктов")
            dialog.geometry("400x150")
            dialog.transient(self.app.root)
            dialog.grab_set()
            dialog.focus_set()

            self.center_window(dialog)

            dialog.lift()
            dialog.attributes('-topmost', True)
            dialog.after(100, lambda: dialog.attributes('-topmost', False))

            ttk.Label(dialog, text=f"Введите комментарий для {len(selected)} пунктов:",
                      wraplength=380).pack(pady=10)

            comment_entry = ttk.Entry(dialog, width=50)
            comment_entry.pack(pady=5)
            comment_entry.focus_set()

            def save_comment():
                comment = comment_entry.get().strip()
                for item in selected:
                    self.set_item_status(item, 2, comment if comment else "")
                    # Снимаем выделение
                    self.selection_vars[item].set(False)
                dialog.destroy()
                self.app.update_bulk_buttons()

            def cancel():
                dialog.destroy()

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=10)

            ttk.Button(btn_frame, text="Сохранить", command=save_comment).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=5)

            comment_entry.bind('<Return>', lambda e: save_comment())
            comment_entry.bind('<Escape>', lambda e: cancel())

    def reset_selected(self):
        """Сбрасывает выбранные пункты"""
        selected = self.get_selected_items()
        if selected:
            for item in selected:
                self.set_item_status(item, 0, None)
                # Снимаем выделение
                self.selection_vars[item].set(False)
            self.app.update_bulk_buttons()

    def mark_all_done(self):
        """Помечает все пункты как Done"""
        if messagebox.askyesno("Подтверждение",
                               f"Пометить все пункты вкладки '{self.tab_name}' как Done?"):
            for item in self.items:
                self.set_item_status(item, 1, None)

    def mark_all_bug(self):
        """Помечает все пункты как BUG"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Комментарий для всех багов")
        dialog.geometry("400x150")
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.focus_set()

        self.center_window(dialog)

        dialog.lift()
        dialog.attributes('-topmost', True)
        dialog.after(100, lambda: dialog.attributes('-topmost', False))

        ttk.Label(dialog, text="Введите общий комментарий для всех багов:",
                  wraplength=380).pack(pady=10)

        comment_entry = ttk.Entry(dialog, width=50)
        comment_entry.pack(pady=5)
        comment_entry.focus_set()

        def save_comment():
            comment = comment_entry.get().strip()
            dialog.destroy()

            if messagebox.askyesno("Подтверждение",
                                   f"Пометить все пункты вкладки '{self.tab_name}' как BUG?"):
                for item in self.items:
                    self.set_item_status(item, 2, comment if comment else "")

        def cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Продолжить", command=save_comment).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=5)

        comment_entry.bind('<Return>', lambda e: save_comment())
        comment_entry.bind('<Escape>', lambda e: cancel())

    def reset_all(self):
        """Сбрасывает все пункты"""
        if messagebox.askyesno("Подтверждение",
                               f"Сбросить все пункты вкладки '{self.tab_name}'?"):
            for item in self.items:
                self.set_item_status(item, 0, None)


class BulkOperationsPanel:
    """Панель массовых операций"""

    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ttk.LabelFrame(parent, text="Массовые операции", padding="10")
        self.frame.grid(row=0, column=1, sticky=(tk.N, tk.W, tk.E, tk.S), padx=(10, 0))

        self.done_btn = None
        self.bug_btn = None
        self.reset_btn = None
        self.info_label = None

        self.setup_ui()

    def setup_ui(self):
        """Создает интерфейс панели"""
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill=tk.Y, expand=True)

        # Кнопки массовых операций
        self.done_btn = ttk.Button(button_frame, text="✅ Пометить всё\nкак Done",
                                   command=self.app.mark_all_done,
                                   style="Success.TButton")
        self.done_btn.pack(pady=5, fill=tk.X)

        self.bug_btn = ttk.Button(button_frame, text="⚠ Пометить всё\nкак BUG",
                                  command=self.app.mark_all_bug,
                                  style="Warning.TButton")
        self.bug_btn.pack(pady=5, fill=tk.X)

        self.reset_btn = ttk.Button(button_frame, text="🔄 Сбросить всё",
                                    command=self.app.reset_all,
                                    style="Danger.TButton")
        self.reset_btn.pack(pady=5, fill=tk.X)

        ttk.Separator(button_frame, orient=tk.HORIZONTAL).pack(pady=10, fill=tk.X)

        self.info_label = ttk.Label(button_frame, text="Применяется к\nтекущей вкладке",
                                    justify=tk.CENTER, font=('Arial', 9, 'italic'))
        self.info_label.pack(pady=5)

        # Стили для кнопок
        style = ttk.Style()
        style.configure("Success.TButton", foreground="green")
        style.configure("Warning.TButton", foreground="orange")
        style.configure("Danger.TButton", foreground="red")

    def update_buttons(self, has_selection):
        """Обновляет текст кнопок в зависимости от наличия выделения"""
        if has_selection:
            self.done_btn.config(text="✅ Пометить выбранное\nкак Done")
            self.bug_btn.config(text="⚠ Пометить выбранное\nкак BUG")
            self.reset_btn.config(text="🔄 Сбросить выбранное")
            self.info_label.config(text="Применяется к\nвыбранным пунктам")
        else:
            self.done_btn.config(text="✅ Пометить всё\nкак Done")
            self.bug_btn.config(text="⚠ Пометить всё\nкак BUG")
            self.reset_btn.config(text="🔄 Сбросить всё")
            self.info_label.config(text="Применяется к\nтекущей вкладке")


class StatsPanel:
    """Панель статистики и прогресса"""

    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ttk.Frame(parent)

        self.progress_var = tk.DoubleVar()
        self.total_label = None
        self.done_label = None
        self.bug_label = None
        self.progress_label = None
        self.progress_bar = None

        self.setup_ui()

    def setup_ui(self):
        """Создает интерфейс панели"""
        # Прогресс бар
        progress_frame = ttk.Frame(self.frame)
        progress_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(progress_frame, text="Прогресс:").pack(side=tk.LEFT, padx=5)
        self.progress_bar = ttk.Progressbar(progress_frame, length=300,
                                            variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, padx=5)
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side=tk.LEFT)

        # Статистика
        stats_frame = ttk.Frame(self.frame)
        stats_frame.pack(side=tk.RIGHT, padx=20)

        ttk.Label(stats_frame, text="Всего:").pack(side=tk.LEFT, padx=2)
        self.total_label = ttk.Label(stats_frame, text="0",
                                     font=('Arial', 10, 'bold'))
        self.total_label.pack(side=tk.LEFT, padx=5)

        ttk.Label(stats_frame, text="✅ Done:").pack(side=tk.LEFT, padx=10)
        self.done_label = ttk.Label(stats_frame, text="0",
                                    font=('Arial', 10, 'bold'),
                                    foreground=Config.COLORS["done"])
        self.done_label.pack(side=tk.LEFT, padx=5)

        ttk.Label(stats_frame, text="🐞 BUG:").pack(side=tk.LEFT, padx=10)
        self.bug_label = ttk.Label(stats_frame, text="0",
                                   font=('Arial', 10, 'bold'),
                                   foreground=Config.COLORS["bug"])
        self.bug_label.pack(side=tk.LEFT, padx=5)

    def grid(self, **kwargs):
        """Метод для размещения панели"""
        self.frame.grid(**kwargs)

    def update_stats(self, total, done, bug):
        """Обновляет статистику"""
        self.total_label.config(text=str(total))
        self.done_label.config(text=str(done))
        self.bug_label.config(text=str(bug))

        if total > 0:
            progress = ((done + bug) / total) * 100
            self.progress_var.set(progress)
            self.progress_label.config(text=f"{int(progress)}%")

            # Изменяем цвет прогресс-бара
            bug_percentage = (bug / total) * 100 if total > 0 else 0
            if bug_percentage > 0:
                self.progress_bar['style'] = 'red.Horizontal.TProgressbar'
            elif progress < 30:
                self.progress_bar['style'] = 'yellow.Horizontal.TProgressbar'
            else:
                self.progress_bar['style'] = 'green.Horizontal.TProgressbar'