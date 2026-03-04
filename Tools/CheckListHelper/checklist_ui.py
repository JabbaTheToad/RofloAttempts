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
        self.selection_vars = {}

        self.frame = ttk.Frame(parent)
        self.setup_ui()

    def setup_ui(self):
        """Создает интерфейс вкладки"""
        # Используем Canvas для прокрутки
        self.canvas = tk.Canvas(self.frame, height=Config.CANVAS_HEIGHT, highlightthickness=0)

        # Вертикальный скроллбар
        self.v_scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)

        # Создаем фрейм для содержимого (используем tk.Frame для простоты)
        self.scrollable_frame = tk.Frame(self.canvas)

        # Настраиваем прокрутку
        self.scrollable_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", tags="inner_frame")
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        # Размещаем элементы
        self.canvas.pack(side="left", fill="both", expand=True)
        self.v_scrollbar.pack(side="right", fill="y")

        # Создаем пункты с задержкой для плавности
        self.create_items_batch()

    def _on_frame_configure(self, event):
        """Обновляет область прокрутки при изменении размера фрейма"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Обновляет ширину внутреннего фрейма при изменении размера canvas"""
        # Устанавливаем ширину внутреннего фрейма равной ширине canvas
        self.canvas.itemconfig("inner_frame", width=event.width)

    def create_items_batch(self, start=0, batch_size=20):
        """Создает пункты пакетами для плавности"""
        end = min(start + batch_size, len(self.items))

        for i in range(start, end):
            self.create_item(self.scrollable_frame, self.items[i], i)

        if end < len(self.items):
            # Создаем следующие пункты с небольшой задержкой
            self.frame.after(10, lambda: self.create_items_batch(end, batch_size))

    def create_item(self, parent, item, row):
        """Создает отдельный пункт с чекбоксом для выбора справа"""
        # Используем tk.Frame вместо ttk.Frame для лучшего контроля цветов
        frame = tk.Frame(parent)
        frame.grid(row=row, column=0, sticky=tk.EW, pady=1)
        frame.columnconfigure(1, weight=1)

        # Получаем стандартный цвет фона
        bg_color = frame.cget('background')

        # Переменная для статуса
        status_var = tk.IntVar()

        # Переменная для выбора пункта
        select_var = tk.BooleanVar()
        self.selection_vars[item] = select_var

        self.checklist_items[item] = {
            "var": status_var,
            "comment": None,
            "frame": frame,
            "select_var": select_var
        }

        # Кнопка для отметки статуса
        status_btn = tk.Button(frame, text="⚪", width=2, relief=tk.FLAT,
                               command=lambda i=item: self.show_status_dialog(i))
        status_btn.grid(row=0, column=0, padx=(0, 2))

        # Текст пункта
        text_label = tk.Label(frame, text=item, anchor=tk.W, bg=bg_color)
        text_label.grid(row=0, column=1, sticky=tk.W, padx=2)

        # Метка для комментария
        comment_label = tk.Label(frame, text="", foreground="red",
                                 font=('Arial', 9, 'italic'), bg=bg_color)
        comment_label.grid(row=0, column=2, sticky=tk.W, padx=2)

        # Чекбокс для выбора пункта (ttk.Checkbutton для единообразия)
        select_cb = ttk.Checkbutton(frame, variable=select_var,
                                    command=self.on_selection_change)
        select_cb.grid(row=0, column=3, padx=(2, 0))

        self.checklist_items[item]["btn"] = status_btn
        self.checklist_items[item]["text_label"] = text_label
        self.checklist_items[item]["comment_label"] = comment_label
        self.checklist_items[item]["select_cb"] = select_cb

    def on_selection_change(self):
        """Обработчик изменения выделения"""
        # Используем after для отложенного вызова, чтобы не тормозить интерфейс
        self.frame.after(10, self.app.update_bulk_buttons)

    def get_selected_items(self):
        """Возвращает список выбранных пунктов"""
        return [item for item, var in self.selection_vars.items() if var.get()]

    def center_window(self, window):
        """Центрирует окно относительно главного окна"""
        # Обновляем геометрию окна
        window.update_idletasks()

        # Получаем размеры главного окна
        main_x = self.app.root.winfo_x()
        main_y = self.app.root.winfo_y()
        main_width = self.app.root.winfo_width()
        main_height = self.app.root.winfo_height()

        # Получаем размеры дочернего окна
        window_width = window.winfo_width()
        window_height = window.winfo_height()

        # Вычисляем координаты для центрирования
        x = main_x + (main_width // 2) - (window_width // 2)
        y = main_y + (main_height // 2) - (window_height // 2)

        # Устанавливаем позицию окна
        window.geometry(f"+{x}+{y}")

        # Делаем окно модальным и поверх всех
        window.transient(self.app.root)
        window.grab_set()
        window.focus_set()
        window.lift()
        window.attributes('-topmost', True)
        window.after(100, lambda: window.attributes('-topmost', False))

    def show_status_dialog(self, item):
        """Показывает диалог выбора статуса"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Выберите статус")
        dialog.geometry("300x150")
        dialog.resizable(False, False)

        # Центрируем окно
        self.center_window(dialog)

        ttk.Label(dialog, text=f"Пункт: {item}", wraplength=280).pack(pady=10)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        def set_done():
            self.set_item_status(item, 1, None)
            dialog.destroy()

        def set_bug():
            dialog.destroy()
            # Показываем диалог комментария
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
        dialog.resizable(False, False)

        # Центрируем окно
        self.center_window(dialog)

        ttk.Label(dialog, text=f"Опишите баг для: {item}", wraplength=380).pack(pady=10)

        # Создаем текстовое поле с поддержкой Ctrl+V
        comment_entry = tk.Text(dialog, width=40, height=3, wrap=tk.WORD)
        comment_entry.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        # Добавляем скроллбар для текстового поля
        scrollbar = ttk.Scrollbar(comment_entry, command=comment_entry.yview)
        comment_entry.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Устанавливаем фокус
        comment_entry.focus_set()

        # Привязываем сочетания клавиш
        def on_ctrl_v(event):
            try:
                # Получаем текст из буфера обмена
                clipboard_text = dialog.clipboard_get()
                # Вставляем в текущую позицию курсора
                comment_entry.insert(tk.INSERT, clipboard_text)
                return "break"  # Предотвращаем дальнейшую обработку
            except tk.TclError:
                # Если буфер обмена пуст, игнорируем
                pass

        def on_ctrl_a(event):
            comment_entry.tag_add(tk.SEL, "1.0", tk.END)
            comment_entry.mark_set(tk.INSERT, "1.0")
            comment_entry.see(tk.INSERT)
            return "break"

        def on_ctrl_x(event):
            try:
                if comment_entry.tag_ranges(tk.SEL):
                    selected_text = comment_entry.get(tk.SEL_FIRST, tk.SEL_LAST)
                    dialog.clipboard_clear()
                    dialog.clipboard_append(selected_text)
                    comment_entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
                return "break"
            except:
                pass

        def on_ctrl_c(event):
            try:
                if comment_entry.tag_ranges(tk.SEL):
                    selected_text = comment_entry.get(tk.SEL_FIRST, tk.SEL_LAST)
                    dialog.clipboard_clear()
                    dialog.clipboard_append(selected_text)
                return "break"
            except:
                pass

        # Привязываем события
        comment_entry.bind('<Control-v>', on_ctrl_v)
        comment_entry.bind('<Control-V>', on_ctrl_v)
        comment_entry.bind('<Control-a>', on_ctrl_a)
        comment_entry.bind('<Control-A>', on_ctrl_a)
        comment_entry.bind('<Control-x>', on_ctrl_x)
        comment_entry.bind('<Control-X>', on_ctrl_x)
        comment_entry.bind('<Control-c>', on_ctrl_c)
        comment_entry.bind('<Control-C>', on_ctrl_c)

        def save_comment():
            comment = comment_entry.get(1.0, tk.END).strip()
            self.set_item_status(item, 2, comment if comment else "")
            dialog.destroy()

        def cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Сохранить", command=save_comment).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=5)

        # Привязываем Enter к сохранению
        comment_entry.bind('<Control-Return>', lambda e: save_comment())
        comment_entry.bind('<Escape>', lambda e: cancel())

    def set_item_status(self, item, status, comment):
        """Устанавливает статус пункта"""
        # Проверяем, существует ли такой пункт в текущей вкладке
        if item not in self.checklist_items:
            print(f"Предупреждение: Пункт '{item}' не найден в вкладке '{self.tab_name}'")
            return

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
                # Ограничиваем длину отображаемого комментария
                short_comment = comment[:30] + "..." if len(comment) > 30 else comment
                comment_label.config(text=f"💬 {short_comment}")
        else:  # None
            btn.config(text="⚪", bg="SystemButtonFace")
            comment_label.config(text="")

        # Сохраняем в модель с задержкой для производительности
        self.frame.after(50, lambda: self.app.save_item_status(
            self.tab_name, item, status, comment))

    def get_item_status(self, item):
        """Возвращает статус пункта"""
        if item in self.checklist_items:
            return self.checklist_items[item]["var"].get()
        return 0  # Возвращаем 0 если пункт не найден

    def mark_selected_done(self):
        """Помечает выбранные пункты как Done"""
        selected = self.get_selected_items()
        if selected:
            # Обновляем с задержкой для плавности
            for item in selected:
                self.frame.after(10, lambda i=item: self.set_item_status(i, 1, None))
                self.selection_vars[item].set(False)
            self.frame.after(100, self.app.update_bulk_buttons)

    def mark_selected_bug(self):
        """Помечает выбранные пункты как BUG"""
        selected = self.get_selected_items()
        if selected:
            dialog = tk.Toplevel(self.app.root)
            dialog.title("Комментарий для выбранных пунктов")
            dialog.geometry("400x150")
            dialog.resizable(False, False)

            self.center_window(dialog)

            ttk.Label(dialog, text=f"Введите комментарий для {len(selected)} пунктов:",
                      wraplength=380).pack(pady=10)

            # Текстовое поле с поддержкой Ctrl+V
            comment_entry = tk.Text(dialog, width=40, height=3, wrap=tk.WORD)
            comment_entry.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

            scrollbar = ttk.Scrollbar(comment_entry, command=comment_entry.yview)
            comment_entry.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            comment_entry.focus_set()

            # Привязываем сочетания клавиш
            def on_ctrl_v(event):
                try:
                    clipboard_text = dialog.clipboard_get()
                    comment_entry.insert(tk.INSERT, clipboard_text)
                    return "break"
                except tk.TclError:
                    pass

            def on_ctrl_a(event):
                comment_entry.tag_add(tk.SEL, "1.0", tk.END)
                comment_entry.mark_set(tk.INSERT, "1.0")
                comment_entry.see(tk.INSERT)
                return "break"

            comment_entry.bind('<Control-v>', on_ctrl_v)
            comment_entry.bind('<Control-V>', on_ctrl_v)
            comment_entry.bind('<Control-a>', on_ctrl_a)
            comment_entry.bind('<Control-A>', on_ctrl_a)

            def save_comment():
                comment = comment_entry.get(1.0, tk.END).strip()
                for item in selected:
                    self.frame.after(10, lambda i=item: self.set_item_status(i, 2, comment))
                    self.selection_vars[item].set(False)
                dialog.destroy()
                self.frame.after(100, self.app.update_bulk_buttons)

            def cancel():
                dialog.destroy()

            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=10)

            ttk.Button(btn_frame, text="Сохранить", command=save_comment).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=5)

            comment_entry.bind('<Control-Return>', lambda e: save_comment())
            comment_entry.bind('<Escape>', lambda e: cancel())

    def reset_selected(self):
        """Сбрасывает выбранные пункты"""
        selected = self.get_selected_items()
        if selected:
            for item in selected:
                self.frame.after(10, lambda i=item: self.set_item_status(i, 0, None))
                self.selection_vars[item].set(False)
            self.frame.after(100, self.app.update_bulk_buttons)

    def mark_all_done(self):
        """Помечает все пункты как Done"""
        if messagebox.askyesno("Подтверждение",
                               f"Пометить все пункты вкладки '{self.tab_name}' как Done?"):
            for item in self.items:
                self.frame.after(10, lambda i=item: self.set_item_status(i, 1, None))

    def mark_all_bug(self):
        """Помечает все пункты как BUG"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Комментарий для всех багов")
        dialog.geometry("400x150")
        dialog.resizable(False, False)

        self.center_window(dialog)

        ttk.Label(dialog, text="Введите общий комментарий для всех багов:",
                  wraplength=380).pack(pady=10)

        # Текстовое поле с поддержкой Ctrl+V
        comment_entry = tk.Text(dialog, width=40, height=3, wrap=tk.WORD)
        comment_entry.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(comment_entry, command=comment_entry.yview)
        comment_entry.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        comment_entry.focus_set()

        # Привязываем сочетания клавиш
        def on_ctrl_v(event):
            try:
                clipboard_text = dialog.clipboard_get()
                comment_entry.insert(tk.INSERT, clipboard_text)
                return "break"
            except tk.TclError:
                pass

        def on_ctrl_a(event):
            comment_entry.tag_add(tk.SEL, "1.0", tk.END)
            comment_entry.mark_set(tk.INSERT, "1.0")
            comment_entry.see(tk.INSERT)
            return "break"

        comment_entry.bind('<Control-v>', on_ctrl_v)
        comment_entry.bind('<Control-V>', on_ctrl_v)
        comment_entry.bind('<Control-a>', on_ctrl_a)
        comment_entry.bind('<Control-A>', on_ctrl_a)

        def save_comment():
            comment = comment_entry.get(1.0, tk.END).strip()
            dialog.destroy()

            if messagebox.askyesno("Подтверждение",
                                   f"Пометить все пункты вкладки '{self.tab_name}' как BUG?"):
                for item in self.items:
                    self.frame.after(10, lambda i=item: self.set_item_status(i, 2, comment))

        def cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Продолжить", command=save_comment).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=cancel).pack(side=tk.LEFT, padx=5)

        comment_entry.bind('<Control-Return>', lambda e: save_comment())
        comment_entry.bind('<Escape>', lambda e: cancel())

    def reset_all(self):
        """Сбрасывает все пункты"""
        if messagebox.askyesno("Подтверждение",
                               f"Сбросить все пункты вкладки '{self.tab_name}'?"):
            for item in self.items:
                self.frame.after(10, lambda i=item: self.set_item_status(i, 0, None))


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