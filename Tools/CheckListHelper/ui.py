import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import os
import subprocess
import platform
from datetime import datetime
from config import Config, get_exports_dir
from models import ProjectModel
from templates import TemplateManager
from checklist_ui import ChecklistTab, BulkOperationsPanel, StatsPanel
from export import ExportManager


class ChecklistApp:
    def __init__(self, root):
        self.root = root
        self.root.title(Config.APP_TITLE)
        self.root.geometry(Config.APP_GEOMETRY)

        # Инициализация менеджеров
        self.project_model = ProjectModel()
        self.template_manager = TemplateManager()
        self.export_manager = ExportManager()

        # Загружаем данные
        self.project_model.load_data()

        # UI элементы
        self.projects_tree = None
        self.type_label = None
        self.current_name_label = None
        self.current_version_label = None
        self.template_combobox = None
        self.notebook = None
        self.checklist_tabs = {}
        self.bulk_panel = None
        self.stats_panel = None
        self.is_loading = False
        self.left_panel_visible = True
        self.left_content = None
        self.main_frame = None
        self.toggle_btn = None
        self.left_header = None
        self.current_item_frame = None

        # Переменная для пути экспорта
        self.exports_dir = tk.StringVar(value=get_exports_dir())

        # Создаем интерфейс
        self.setup_ui()

    def setup_ui(self):
        """Создание пользовательского интерфейса"""
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

        # Левая панель (с кнопкой в заголовке)
        self.setup_left_panel()

        # Правая панель
        self.setup_right_panel()

        # Настройка весов
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Обновляем дерево проектов
        self.update_projects_tree()

    def setup_left_panel(self):
        """Создание левой панели с деревом проектов"""
        left_container = ttk.Frame(self.main_frame)
        left_container.grid(row=0, column=0, rowspan=2, sticky=(tk.N, tk.W, tk.E, tk.S), padx=(0, 10))
        left_container.columnconfigure(0, weight=1)
        left_container.rowconfigure(1, weight=1)

        # Заголовок с кнопкой скрытия
        self.left_header = ttk.Frame(left_container)
        self.left_header.grid(row=0, column=0, sticky=tk.EW, pady=(0, 5))

        ttk.Label(self.left_header, text="Проекты и объекты", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        self.toggle_btn = ttk.Button(self.left_header, text="◀", width=3,
                                     command=self.toggle_left_panel)
        self.toggle_btn.pack(side=tk.RIGHT)

        # Содержимое левой панели
        self.left_content = ttk.Frame(left_container)
        self.left_content.grid(row=1, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        self.left_content.columnconfigure(0, weight=1)
        self.left_content.rowconfigure(1, weight=1)

        # Кнопки управления
        btn_frame = ttk.Frame(self.left_content)
        btn_frame.grid(row=0, column=0, sticky=tk.EW, pady=5)

        ttk.Button(btn_frame, text="➕ Проект",
                   command=self.add_project_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="➕ Объект",
                   command=self.add_object_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✏️ Переименовать",
                   command=self.rename_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️ Удалить",
                   command=self.delete_item).pack(side=tk.LEFT, padx=2)

        # Дерево проектов с прокруткой
        tree_frame = ttk.Frame(self.left_content)
        tree_frame.grid(row=1, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        tree_scrollbar = ttk.Scrollbar(tree_frame)
        tree_scrollbar.grid(row=0, column=1, sticky=tk.NS)

        self.projects_tree = ttk.Treeview(tree_frame, columns=("version", "template"),
                                          selectmode="browse",
                                          yscrollcommand=tree_scrollbar.set)
        self.projects_tree.heading("#0", text="Название")
        self.projects_tree.heading("version", text="Версия")
        self.projects_tree.heading("template", text="Шаблон")
        self.projects_tree.column("#0", width=Config.TREE_COLUMN_WIDTHS["name"])
        self.projects_tree.column("version", width=Config.TREE_COLUMN_WIDTHS["version"])
        self.projects_tree.column("template", width=Config.TREE_COLUMN_WIDTHS["template"])

        self.projects_tree.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        tree_scrollbar.config(command=self.projects_tree.yview)

        self.projects_tree.bind('<<TreeviewSelect>>', self.on_tree_select)

    def setup_right_panel(self):
        """Создание правой панели с чек-листами"""
        right_container = ttk.Frame(self.main_frame)
        right_container.grid(row=0, column=1, rowspan=2, sticky=(tk.N, tk.W, tk.E, tk.S))
        right_container.columnconfigure(0, weight=1)
        right_container.rowconfigure(1, weight=1)

        # Верхний блок с информацией о текущем элементе и настройками
        self.setup_info_block(right_container)

        # Основной блок с чек-листами
        self.setup_checklist_block(right_container)

        # Нижний блок с выбором шаблона
        self.setup_template_block(right_container)

    def setup_info_block(self, parent):
        """Создает блок с информацией о текущем элементе"""
        info_block = ttk.LabelFrame(parent, text="Текущий элемент", padding="10")
        info_block.grid(row=0, column=0, sticky=tk.EW, pady=(0, 10))
        info_block.columnconfigure(1, weight=1)

        # Тип элемента
        ttk.Label(info_block, text="Тип:", font=('Arial', 9)).grid(row=0, column=0, sticky=tk.W, padx=5)
        self.type_label = ttk.Label(info_block, text="—", font=('Arial', 9, 'bold'))
        self.type_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        # Название
        ttk.Label(info_block, text="Название:", font=('Arial', 9)).grid(row=0, column=2, sticky=tk.W, padx=(20, 5))
        self.current_name_label = ttk.Label(info_block, text="—", font=('Arial', 9))
        self.current_name_label.grid(row=0, column=3, sticky=tk.W, padx=5)

        # Версия
        ttk.Label(info_block, text="Версия:", font=('Arial', 9)).grid(row=0, column=4, sticky=tk.W, padx=(20, 5))
        self.current_version_label = ttk.Label(info_block, text="—", font=('Arial', 9))
        self.current_version_label.grid(row=0, column=5, sticky=tk.W, padx=5)

        # Кнопка настроек
        settings_btn = ttk.Button(info_block, text="⚙️", width=3,
                                  command=self.show_settings_dialog)
        settings_btn.grid(row=0, column=6, padx=(20, 5))

    def setup_checklist_block(self, parent):
        """Создает блок с чек-листами и массовыми операциями"""
        checklist_block = ttk.Frame(parent)
        checklist_block.grid(row=1, column=0, sticky=(tk.N, tk.W, tk.E, tk.S), pady=10)
        checklist_block.columnconfigure(0, weight=1)
        checklist_block.rowconfigure(0, weight=1)

        # Горизонтальный контейнер для чек-листов и массовых операций
        horizontal_container = ttk.Frame(checklist_block)
        horizontal_container.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        horizontal_container.columnconfigure(0, weight=1)
        horizontal_container.rowconfigure(0, weight=1)

        # Ноутбук с чек-листами
        notebook_frame = ttk.Frame(horizontal_container)
        notebook_frame.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))
        notebook_frame.columnconfigure(0, weight=1)
        notebook_frame.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        # Привязываем событие смены вкладки
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)

        # Панель массовых операций
        self.bulk_panel = BulkOperationsPanel(horizontal_container, self)

        # Панель статистики
        self.stats_panel = StatsPanel(checklist_block, self)
        self.stats_panel.grid(row=1, column=0, pady=(10, 0), sticky=tk.EW)

    def setup_template_block(self, parent):
        """Создает блок выбора шаблона"""
        template_block = ttk.LabelFrame(parent, text="Шаблон чек-листов", padding="10")
        template_block.grid(row=2, column=0, sticky=tk.EW, pady=(10, 0))
        template_block.columnconfigure(1, weight=1)

        ttk.Label(template_block, text="Выберите шаблон:").grid(row=0, column=0, sticky=tk.W, padx=5)

        self.template_combobox = ttk.Combobox(template_block,
                                              values=self.template_manager.get_template_names(),
                                              state="readonly", width=40)
        self.template_combobox.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Button(template_block, text="Применить шаблон",
                   command=self.apply_template_to_project).grid(row=0, column=2, padx=5)

    def toggle_left_panel(self):
        """Скрывает или показывает содержимое левой панели"""
        if self.left_panel_visible:
            self.left_content.grid_remove()
            self.toggle_btn.config(text="▶")
            self.left_panel_visible = False
        else:
            self.left_content.grid()
            self.toggle_btn.config(text="◀")
            self.left_panel_visible = True

    def center_window(self, window):
        """Центрирует окно относительно главного"""
        window.update_idletasks()

        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()

        window_width = window.winfo_width()
        window_height = window.winfo_height()

        x = main_x + (main_width // 2) - (window_width // 2)
        y = main_y + (main_height // 2) - (window_height // 2)

        window.geometry(f"+{x}+{y}")

    def show_settings_dialog(self):
        """Показывает диалог настроек"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки")
        dialog.geometry("650x550")
        dialog.transient(self.root)
        dialog.grab_set()

        self.center_window(dialog)

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.setup_templates_tab(notebook)
        self.setup_export_tab(notebook)

    def setup_templates_tab(self, notebook):
        """Создает вкладку управления шаблонами"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Управление шаблонами")

        list_frame = ttk.LabelFrame(tab, text="Доступные шаблоны", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        template_listbox = tk.Listbox(list_frame, height=15)
        template_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=template_listbox.yview)
        template_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for template_name in self.template_manager.get_template_names():
            template_listbox.insert(tk.END, template_name)

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(btn_frame, text="📁 Загрузить шаблон",
                   command=lambda: self.import_template_from_settings(template_listbox)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="➕ Новый шаблон",
                   command=lambda: self.create_template_from_settings(template_listbox)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="✏️ Редактировать",
                   command=lambda: self.edit_template_from_settings(template_listbox)).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="🗑️ Удалить",
                   command=lambda: self.delete_template(template_listbox)).pack(side=tk.LEFT, padx=2)

    def open_exports_folder(self):
        """Открывает папку с отчетами в проводнике"""
        exports_dir = self.exports_dir.get()

        if not os.path.exists(exports_dir):
            os.makedirs(exports_dir)

        try:
            if platform.system() == 'Windows':
                os.startfile(exports_dir)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', exports_dir])
            else:  # Linux
                subprocess.run(['xdg-open', exports_dir])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

    def choose_exports_folder(self):
        """Открывает диалог выбора папки для отчетов"""
        folder = filedialog.askdirectory(
            title="Выберите папку для сохранения отчетов",
            initialdir=self.exports_dir.get()
        )

        if folder:
            self.exports_dir.set(folder)
            messagebox.showinfo("Успех", f"Папка для отчетов изменена на:\n{folder}")

    def setup_export_tab(self, notebook):
        """Создает вкладку экспорта"""
        tab = ttk.Frame(notebook)
        notebook.add(tab, text="Экспорт результатов")

        # Информация о текущем проекте
        info_frame = ttk.LabelFrame(tab, text="Текущий проект", padding="10")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        if self.project_model.current_project:
            ttk.Label(info_frame, text=f"Проект: {self.project_model.current_project}").pack(anchor=tk.W, pady=2)
            ttk.Label(info_frame,
                      text=f"Версия: {self.project_model.get_project_version(self.project_model.current_project)}").pack(
                anchor=tk.W, pady=2)
            if self.project_model.current_object:
                ttk.Label(info_frame, text=f"Объект: {self.project_model.current_object}").pack(anchor=tk.W, pady=2)
        else:
            ttk.Label(info_frame, text="Проект не выбран").pack(anchor=tk.W, pady=2)

        # Настройки экспорта
        options_frame = ttk.LabelFrame(tab, text="Параметры экспорта", padding="10")
        options_frame.pack(fill=tk.X, padx=10, pady=5)

        # Выбор формата
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, pady=5)

        ttk.Label(format_frame, text="Формат:").pack(side=tk.LEFT, padx=5)
        export_format = tk.StringVar(value="excel")
        ttk.Radiobutton(format_frame, text="Excel", variable=export_format,
                        value="excel").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(format_frame, text="PDF", variable=export_format,
                        value="pdf").pack(side=tk.LEFT, padx=10)

        # Выбор области экспорта
        scope_frame = ttk.Frame(options_frame)
        scope_frame.pack(fill=tk.X, pady=5)

        ttk.Label(scope_frame, text="Область:").pack(side=tk.LEFT, padx=5)
        export_scope = tk.StringVar(value="current")
        ttk.Radiobutton(scope_frame, text="Текущий элемент", variable=export_scope,
                        value="current").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(scope_frame, text="Весь проект", variable=export_scope,
                        value="project").pack(side=tk.LEFT, padx=10)

        # Настройка папки для отчетов
        folder_frame = ttk.LabelFrame(tab, text="Папка для отчетов", padding="10")
        folder_frame.pack(fill=tk.X, padx=10, pady=5)

        # Поле с путем
        path_frame = ttk.Frame(folder_frame)
        path_frame.pack(fill=tk.X, pady=5)

        ttk.Label(path_frame, text="Путь:").pack(side=tk.LEFT, padx=5)
        path_entry = ttk.Entry(path_frame, textvariable=self.exports_dir, width=50)
        path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # Кнопки управления папкой
        folder_buttons = ttk.Frame(folder_frame)
        folder_buttons.pack(fill=tk.X, pady=5)

        ttk.Button(folder_buttons, text="📂 Перейти к отчетам",
                   command=self.open_exports_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(folder_buttons, text="📁 Выбрать другую папку",
                   command=self.choose_exports_folder).pack(side=tk.LEFT, padx=5)

        # Кнопка экспорта
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=20)

        def do_export():
            if not self.project_model.current_project:
                messagebox.showerror("Ошибка", "Сначала выберите проект")
                return

            format_type = export_format.get()
            scope_type = export_scope.get()

            # Обновляем путь экспорта в менеджере
            self.export_manager.exports_dir = self.exports_dir.get()

            data = self.collect_export_data(scope_type)

            if format_type == "excel":
                success, message = self.export_manager.export_to_excel(data)
            else:
                success, message = self.export_manager.export_to_pdf(data)

            if success:
                if messagebox.askyesno("Успех", f"Данные экспортированы:\n{message}\n\nОткрыть папку с отчетом?"):
                    self.open_exports_folder()
            else:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать:\n{message}")

        export_button_frame = ttk.Frame(btn_frame)
        export_button_frame.pack()

        ttk.Button(export_button_frame, text="📊 Экспортировать",
                   command=do_export).pack(side=tk.LEFT, padx=5)

        info_label = ttk.Label(tab, text="Отчеты сохраняются в выбранную папку",
                               font=('Arial', 9, 'italic'), foreground="gray")
        info_label.pack(side=tk.BOTTOM, pady=10)

    def import_template_from_settings(self, listbox):
        """Импортирует шаблон из окна настроек"""
        filename = filedialog.askopenfilename(
            title="Выберите файл шаблона",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if filename:
            success, result = self.template_manager.import_template(filename)
            if success:
                listbox.insert(tk.END, result)
                self.template_combobox['values'] = self.template_manager.get_template_names()
                messagebox.showinfo("Успех", f"Шаблон {result} успешно загружен")
            else:
                messagebox.showerror("Ошибка", f"Не удалось загрузить шаблон: {result}")

    def create_template_from_settings(self, listbox):
        """Создает новый шаблон из окна настроек"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Создать новый шаблон")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()

        self.center_window(dialog)

        ttk.Label(dialog, text="Название шаблона:").pack(pady=5)
        name_entry = ttk.Entry(dialog, width=50)
        name_entry.pack(pady=5)

        ttk.Label(dialog, text="Содержимое шаблона:").pack(pady=5)

        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, width=70, height=20)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        example_frame = ttk.LabelFrame(dialog, text="Пример формата", padding="5")
        example_frame.pack(fill=tk.X, padx=10, pady=5)

        example_text = """Время
- Ползунок
- Ускорить

Настройки
- Кнопка 1
- Кнопка 2"""

        ttk.Label(example_frame, text=example_text, justify=tk.LEFT).pack()

        def save():
            name = name_entry.get().strip()
            content = text_widget.get(1.0, tk.END).strip()

            if not name:
                messagebox.showerror("Ошибка", "Введите название шаблона")
                return

            if not content:
                messagebox.showerror("Ошибка", "Введите содержимое шаблона")
                return

            success, result = self.template_manager.save_template(name, content)
            if success:
                listbox.insert(tk.END, result)
                self.template_combobox['values'] = self.template_manager.get_template_names()
                dialog.destroy()
                messagebox.showinfo("Успех", f"Шаблон {result} создан")
            else:
                messagebox.showerror("Ошибка", f"Не удалось сохранить шаблон: {result}")

        ttk.Button(dialog, text="Сохранить", command=save).pack(pady=10)

    def edit_template_from_settings(self, listbox):
        """Редактирует шаблон из окна настроек"""
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите шаблон для редактирования")
            return

        template_name = listbox.get(selection[0])
        filepath = os.path.join(self.template_manager.templates_dir, template_name)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить шаблон: {e}")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Редактирование шаблона: {template_name}")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()

        self.center_window(dialog)

        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, width=70, height=20)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget.insert(1.0, content)

        def save():
            new_content = text_widget.get(1.0, tk.END).strip()
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.template_manager.load_templates()
                dialog.destroy()
                messagebox.showinfo("Успех", f"Шаблон {template_name} обновлен")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить шаблон: {e}")

        ttk.Button(dialog, text="Сохранить", command=save).pack(pady=10)

    def delete_template(self, listbox):
        """Удаляет шаблон"""
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите шаблон для удаления")
            return

        template_name = listbox.get(selection[0])

        if messagebox.askyesno("Подтверждение", f"Удалить шаблон '{template_name}'?"):
            try:
                filepath = os.path.join(self.template_manager.templates_dir, template_name)
                os.remove(filepath)
                listbox.delete(selection[0])
                self.template_manager.load_templates()
                self.template_combobox['values'] = self.template_manager.get_template_names()
                messagebox.showinfo("Успех", f"Шаблон {template_name} удален")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить шаблон: {e}")

    def update_projects_tree(self):
        """Обновляет дерево проектов и объектов"""
        if self.projects_tree:
            for item in self.projects_tree.get_children():
                self.projects_tree.delete(item)

            for project_name, project_data in self.project_model.projects.items():
                version = project_data.get("version", "—")
                template = project_data.get("template", "—")
                project_id = self.projects_tree.insert("", "end", text=project_name,
                                                       values=(version, template), tags=("project",))

                for object_name in project_data.get("objects", {}).keys():
                    self.projects_tree.insert(project_id, "end", text=object_name,
                                              values=("", ""), tags=("object",))

                self.projects_tree.item(project_id, open=True)

    def on_tree_select(self, event):
        """Обработчик выбора в дереве"""
        selection = self.projects_tree.selection()
        if selection and not self.is_loading:
            item = selection[0]
            parent = self.projects_tree.parent(item)

            self.is_loading = True

            if not parent:
                project_name = self.projects_tree.item(item, "text")
                self.project_model.current_project = project_name
                self.project_model.current_object = None

                self.type_label.config(text="Проект")
                self.current_name_label.config(text=project_name)
                self.current_version_label.config(text=self.project_model.get_project_version(project_name))

                # Загружаем шаблон и создаем вкладки
                template_name = self.project_model.get_project_template(project_name)
                template_data = self.template_manager.get_template_data(template_name)
                self.rebuild_checklists(template_data, is_object=False)

                # Обновляем информацию о текущем элементе
                self.update_progress()

            else:
                project_name = self.projects_tree.item(parent, "text")
                object_name = self.projects_tree.item(item, "text")
                self.project_model.current_project = project_name
                self.project_model.current_object = object_name

                self.type_label.config(text="Объект")
                self.current_name_label.config(text=object_name)
                self.current_version_label.config(text=self.project_model.get_project_version(project_name))

                # Загружаем шаблон и создаем вкладки (только Генплан)
                template_name = self.project_model.get_project_template(project_name)
                template_data = self.template_manager.get_template_data(template_name)
                self.rebuild_checklists(template_data, is_object=True)

                # Обновляем информацию о текущем элементе
                self.update_progress()

            self.is_loading = False

    def rebuild_checklists(self, template_data, is_object=False):
        """Перестраивает чек-листы"""
        # Очищаем текущие вкладки
        for tab in self.notebook.winfo_children():
            tab.destroy()

        self.checklist_tabs = {}

        # Определяем, какие вкладки показывать
        tabs_to_show = template_data.keys()
        if is_object:
            tabs_to_show = ["Генплан"] if "Генплан" in template_data else []

        # Создаем новые вкладки
        for tab_name in tabs_to_show:
            items = template_data.get(tab_name, [])
            tab = ChecklistTab(self.notebook, tab_name, items, self)
            self.notebook.add(tab.frame, text=tab_name)
            self.checklist_tabs[tab_name] = tab

        # Загружаем данные
        self.load_current_data()

    def load_current_data(self):
        """Загружает данные для текущего элемента"""
        if not self.project_model.current_project:
            return

        if not self.project_model.current_object:  # Проект
            for tab_name, tab in self.checklist_tabs.items():
                if tab_name != "Генплан":
                    for item in tab.items:
                        status, comment = self.project_model.get_project_item_status(
                            self.project_model.current_project, tab_name, item)
                        tab.set_item_status(item, status, comment)
        else:  # Объект
            if "Генплан" in self.checklist_tabs:
                for item in self.checklist_tabs["Генплан"].items:
                    status, comment = self.project_model.get_object_item_status(
                        self.project_model.current_project,
                        self.project_model.current_object, item)
                    self.checklist_tabs["Генплан"].set_item_status(item, status, comment)

        self.update_progress()

    def save_item_status(self, tab_name, item, status, comment):
        """Сохраняет статус пункта"""
        if not self.project_model.current_project:
            return

        if not self.project_model.current_object:  # Проект
            self.project_model.save_project_item_status(
                self.project_model.current_project, tab_name, item, status, comment)
        else:  # Объект
            self.project_model.save_object_item_status(
                self.project_model.current_project,
                self.project_model.current_object, item, status, comment)

        self.project_model.save_data()
        self.update_progress()

    def update_progress(self):
        """Обновляет прогресс и статистику"""
        if not self.project_model.current_project or self.is_loading:
            return

        total = 0
        done = 0
        bug = 0

        if not self.project_model.current_object:  # Проект
            for tab_name, tab in self.checklist_tabs.items():
                if tab_name != "Генплан":
                    for item in tab.items:
                        total += 1
                        status = tab.get_item_status(item)
                        if status == 1:
                            done += 1
                        elif status == 2:
                            bug += 1
        else:  # Объект
            if "Генплан" in self.checklist_tabs:
                for item in self.checklist_tabs["Генплан"].items:
                    total += 1
                    status = self.checklist_tabs["Генплан"].get_item_status(item)
                    if status == 1:
                        done += 1
                    elif status == 2:
                        bug += 1

        self.stats_panel.update_stats(total, done, bug)

    def update_bulk_buttons(self):
        """Обновляет кнопки массовых операций"""
        if not self.bulk_panel:
            return

        current_tab = self.get_current_tab()
        if current_tab:
            has_selection = len(current_tab.get_selected_items()) > 0
            self.bulk_panel.update_buttons(has_selection)

    def get_current_tab(self):
        """Возвращает текущую вкладку"""
        current = self.notebook.select()
        if current:
            tab_name = self.notebook.tab(current, "text")
            return self.checklist_tabs.get(tab_name)
        return None

    def on_tab_changed(self, event):
        """Обработчик смены вкладки"""
        self.update_bulk_buttons()

    def mark_all_done(self):
        """Обработчик кнопки Done"""
        current_tab = self.get_current_tab()
        if current_tab:
            selected = current_tab.get_selected_items()
            if selected:
                current_tab.mark_selected_done()
            else:
                current_tab.mark_all_done()

    def mark_all_bug(self):
        """Обработчик кнопки BUG"""
        current_tab = self.get_current_tab()
        if current_tab:
            selected = current_tab.get_selected_items()
            if selected:
                current_tab.mark_selected_bug()
            else:
                current_tab.mark_all_bug()

    def reset_all(self):
        """Обработчик кнопки сброса"""
        current_tab = self.get_current_tab()
        if current_tab:
            selected = current_tab.get_selected_items()
            if selected:
                current_tab.reset_selected()
            else:
                current_tab.reset_all()

    def add_project_dialog(self):
        """Диалог добавления проекта"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить проект")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()

        self.center_window(dialog)

        ttk.Label(dialog, text="Название проекта:").pack(pady=5)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(pady=5)

        ttk.Label(dialog, text="Версия проекта:").pack(pady=5)
        version_entry = ttk.Entry(dialog, width=40)
        version_entry.insert(0, "1.0.0")
        version_entry.pack(pady=5)

        ttk.Label(dialog, text="Выберите шаблон чек-листов:").pack(pady=5)
        template_combo = ttk.Combobox(dialog, values=self.template_manager.get_template_names(),
                                      state="readonly", width=37)
        template_combo.pack(pady=5)
        if self.template_manager.get_template_names():
            template_combo.current(0)

        def save():
            name = name_entry.get().strip()
            version = version_entry.get().strip()
            template = template_combo.get()

            if not name:
                messagebox.showerror("Ошибка", "Введите название проекта")
                return

            if not template:
                messagebox.showerror("Ошибка", "Выберите шаблон")
                return

            if self.project_model.add_project(name, version, template):
                template_data = self.template_manager.get_template_data(template)
                self.project_model.init_project_checklists(name, template_data)
                self.project_model.save_data()
                self.update_projects_tree()
                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Проект с таким названием уже существует")

        ttk.Button(dialog, text="Сохранить", command=save).pack(pady=10)

    def add_object_dialog(self):
        """Диалог добавления объекта"""
        if not self.project_model.current_project:
            messagebox.showwarning("Внимание", "Сначала выберите проект")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить объект")
        dialog.geometry("350x150")
        dialog.transient(self.root)
        dialog.grab_set()

        self.center_window(dialog)

        ttk.Label(dialog, text=f"Проект: {self.project_model.current_project}").pack(pady=5)
        ttk.Label(dialog, text="Название объекта:").pack(pady=5)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(pady=5)

        def save():
            name = name_entry.get().strip()
            if name:
                if self.project_model.add_object(self.project_model.current_project, name):
                    template_name = self.project_model.get_project_template(self.project_model.current_project)
                    template_data = self.template_manager.get_template_data(template_name)
                    self.project_model.init_object_checklists(
                        self.project_model.current_project, name, template_data)
                    self.project_model.save_data()
                    self.update_projects_tree()
                    dialog.destroy()
                else:
                    messagebox.showerror("Ошибка", "Объект с таким названием уже существует")
            else:
                messagebox.showerror("Ошибка", "Введите название объекта")

        ttk.Button(dialog, text="Сохранить", command=save).pack(pady=10)

    def rename_item(self):
        """Переименовывает выбранный элемент"""
        selection = self.projects_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите элемент для переименования")
            return

        item = selection[0]
        parent = self.projects_tree.parent(item)
        old_name = self.projects_tree.item(item, "text")

        if not parent:
            new_name = simpledialog.askstring("Переименовать проект",
                                              "Новое название:",
                                              initialvalue=old_name)
            if new_name and new_name != old_name:
                if self.project_model.rename_project(old_name, new_name):
                    if self.project_model.current_project == old_name:
                        self.project_model.current_project = new_name
                    self.project_model.save_data()
                    self.update_projects_tree()
                else:
                    messagebox.showerror("Ошибка", "Проект с таким названием уже существует")

        else:
            project_name = self.projects_tree.item(parent, "text")
            new_name = simpledialog.askstring("Переименовать объект",
                                              "Новое название:",
                                              initialvalue=old_name)
            if new_name and new_name != old_name:
                if self.project_model.rename_object(project_name, old_name, new_name):
                    if self.project_model.current_object == old_name:
                        self.project_model.current_object = new_name
                    self.project_model.save_data()
                    self.update_projects_tree()
                else:
                    messagebox.showerror("Ошибка", "Объект с таким названием уже существует")

    def delete_item(self):
        """Удаляет выбранный элемент"""
        selection = self.projects_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите элемент для удаления")
            return

        item = selection[0]
        parent = self.projects_tree.parent(item)
        name = self.projects_tree.item(item, "text")

        if not parent:
            if messagebox.askyesno("Подтверждение", f"Удалить проект '{name}'?"):
                if self.project_model.delete_project(name):
                    if self.project_model.current_project == name:
                        self.project_model.current_project = None
                        self.project_model.current_object = None
                        self.type_label.config(text="—")
                        self.current_name_label.config(text="—")
                        self.current_version_label.config(text="—")

                        # Очищаем чек-листы
                        for tab in self.notebook.winfo_children():
                            tab.destroy()
                        self.checklist_tabs = {}
                        self.stats_panel.update_stats(0, 0, 0)

                    self.project_model.save_data()
                    self.update_projects_tree()

        else:
            project_name = self.projects_tree.item(parent, "text")
            if messagebox.askyesno("Подтверждение", f"Удалить объект '{name}'?"):
                if self.project_model.delete_object(project_name, name):
                    if self.project_model.current_object == name:
                        self.project_model.current_object = None

                        # Перезагружаем проект (без объекта)
                        template_name = self.project_model.get_project_template(project_name)
                        template_data = self.template_manager.get_template_data(template_name)
                        self.rebuild_checklists(template_data, is_object=False)

                        self.type_label.config(text="Проект")
                        self.current_name_label.config(text=project_name)

                    self.project_model.save_data()
                    self.update_projects_tree()

    def apply_template_to_project(self):
        """Применяет шаблон к проекту"""
        if not self.project_model.current_project:
            messagebox.showwarning("Внимание", "Сначала выберите проект")
            return

        if not self.template_combobox.get():
            messagebox.showwarning("Внимание", "Выберите шаблон")
            return

        template_name = self.template_combobox.get()
        template_data = self.template_manager.get_template_data(template_name)

        self.project_model.update_project_template(self.project_model.current_project, template_name)
        self.project_model.init_project_checklists(self.project_model.current_project, template_data)

        for object_name in self.project_model.projects[self.project_model.current_project].get("objects", {}):
            self.project_model.init_object_checklists(
                self.project_model.current_project, object_name, template_data)

        self.project_model.save_data()

        if self.project_model.current_object:
            self.rebuild_checklists(template_data, is_object=True)
            self.load_current_data()
        else:
            self.rebuild_checklists(template_data, is_object=False)
            self.load_current_data()

        self.update_projects_tree()
        messagebox.showinfo("Успех", f"Шаблон {template_name} применен к проекту")

    def collect_export_data(self, scope):
        """Собирает данные для экспорта"""
        data = {
            "project_name": self.project_model.current_project,
            "project_version": self.project_model.get_project_version(self.project_model.current_project),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sections": []
        }

        if scope == "current" and self.project_model.current_object:
            data["type"] = "object"
            data["object_name"] = self.project_model.current_object
            section = self.collect_object_data(self.project_model.current_project,
                                               self.project_model.current_object)
            if section:
                data["sections"].append(section)

        elif scope == "current" and not self.project_model.current_object:
            data["type"] = "project_common"
            section = self.collect_project_common_data(self.project_model.current_project)
            if section:
                data["sections"].append(section)

        else:
            data["type"] = "full_project"
            common_section = self.collect_project_common_data(self.project_model.current_project)
            if common_section:
                data["sections"].append(common_section)

            project_data = self.project_model.projects[self.project_model.current_project]
            for object_name in project_data.get("objects", {}):
                object_section = self.collect_object_data(self.project_model.current_project, object_name)
                if object_section:
                    data["sections"].append(object_section)

        return data

    def collect_project_common_data(self, project_name):
        """Собирает данные общих чек-листов проекта"""
        if not self.checklist_tabs:
            return None

        section = {
            "name": "Общие чек-листы",
            "tabs": []
        }

        for tab_name, tab in self.checklist_tabs.items():
            if tab_name != "Генплан":
                tab_data = {
                    "name": tab_name,
                    "items": []
                }
                for item in tab.items:
                    status = tab.get_item_status(item)
                    comment = tab.checklist_items[item]["comment"]
                    tab_data["items"].append({
                        "name": item,
                        "status": status,
                        "status_text": "Done" if status == 1 else "BUG" if status == 2 else "—",
                        "comment": comment or ""
                    })
                section["tabs"].append(tab_data)

        return section

    def collect_object_data(self, project_name, object_name):
        """Собирает данные объекта"""
        if "Генплан" not in self.checklist_tabs:
            return None

        tab = self.checklist_tabs["Генплан"]
        section = {
            "name": f"Объект: {object_name}",
            "tabs": [{
                "name": "Генплан",
                "items": []
            }]
        }

        for item in tab.items:
            status = tab.get_item_status(item)
            comment = tab.checklist_items[item]["comment"]
            section["tabs"][0]["items"].append({
                "name": item,
                "status": status,
                "status_text": "Done" if status == 1 else "BUG" if status == 2 else "—",
                "comment": comment or ""
            })

        return section