import sys
import json
import os
from datetime import datetime, date, timedelta
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QComboBox, QLineEdit, QLabel, QMessageBox, QSystemTrayIcon,
                             QMenu, QTextEdit, QDialog, QTabWidget, QInputDialog,
                             QDialogButtonBox, QRadioButton, QButtonGroup, QListWidget,
                             QListWidgetItem, QFrame, QSplitter, QScrollArea)
from PyQt5.QtCore import QTimer, Qt, QDateTime, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QIcon, QFont, QColor

# Имя файла для хранения данных
DATA_FILE = 'time_stats.json'


class DeleteProjectDialog(QDialog):
    """Диалог для удаления проекта с выбором действия"""

    def __init__(self, project_name, has_time, other_projects, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self.has_time = has_time
        self.other_projects = other_projects
        self.selected_action = None
        self.selected_project = None

        self.setWindowTitle(f"Удаление проекта: {project_name}")
        self.setGeometry(400, 300, 400, 200)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout()

        if has_time:
            layout.addWidget(QLabel(f"⚠ Проект '{project_name}' содержит учтенное время."))
            layout.addWidget(QLabel("Выберите действие:"))
            layout.addSpacing(10)

            self.radio_group = QButtonGroup(self)

            self.radio_delete = QRadioButton("🗑 Удалить проект и всё затраченное время")
            self.radio_delete.setChecked(True)
            self.radio_group.addButton(self.radio_delete, 1)
            layout.addWidget(self.radio_delete)

            self.radio_transfer = QRadioButton("📦 Удалить проект, перенести время в другой проект")
            self.radio_group.addButton(self.radio_transfer, 2)
            layout.addWidget(self.radio_transfer)

            layout.addSpacing(10)

            transfer_layout = QHBoxLayout()
            transfer_layout.addWidget(QLabel("Перенести время в:"))
            self.project_combo = QComboBox()
            self.project_combo.addItems(self.other_projects)
            transfer_layout.addWidget(self.project_combo)
            layout.addLayout(transfer_layout)

            layout.addWidget(QLabel("ℹ Все данные по дням будут перенесены в выбранный проект"))
        else:
            layout.addWidget(QLabel(f"Удалить проект '{project_name}'?"))
            layout.addWidget(QLabel("В проекте нет учтенного времени."))

        layout.addSpacing(20)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_action(self):
        if self.has_time:
            if self.radio_delete.isChecked():
                return 'delete', None
            else:
                return 'transfer', self.project_combo.currentText()
        else:
            return 'delete', None


class StatisticsDialog(QDialog):
    """Отдельный класс для окна статистики"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("📊 Статистика")
        self.setGeometry(400, 300, 600, 500)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout()

        self.tabs = QTabWidget()

        # Вкладка "Сегодня"
        self.today_widget = QWidget()
        today_layout = QVBoxLayout()
        self.today_text = QTextEdit()
        self.today_text.setReadOnly(True)
        self.today_text.setFont(QFont("Courier", 10))
        today_layout.addWidget(self.today_text)
        self.today_widget.setLayout(today_layout)
        self.tabs.addTab(self.today_widget, "Сегодня")

        # Вкладка "Неделя"
        self.week_widget = QWidget()
        week_layout = QVBoxLayout()
        self.week_text = QTextEdit()
        self.week_text.setReadOnly(True)
        self.week_text.setFont(QFont("Courier", 10))
        week_layout.addWidget(self.week_text)
        self.week_widget.setLayout(week_layout)
        self.tabs.addTab(self.week_widget, "Неделя")

        # Вкладка "Месяц"
        self.month_widget = QWidget()
        month_layout = QVBoxLayout()
        self.month_text = QTextEdit()
        self.month_text.setReadOnly(True)
        self.month_text.setFont(QFont("Courier", 10))
        month_layout.addWidget(self.month_text)
        self.month_widget.setLayout(month_layout)
        self.tabs.addTab(self.month_widget, "Месяц")

        button_layout = QHBoxLayout()
        update_btn = QPushButton("🔄 Обновить")
        update_btn.clicked.connect(self.update_reports)
        close_btn = QPushButton("✕ Закрыть")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(update_btn)
        button_layout.addWidget(close_btn)

        layout.addWidget(self.tabs)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.update_reports()

    def update_reports(self):
        if self.parent:
            self.today_text.setText(self.parent.get_today_report())
            self.week_text.setText(self.parent.get_period_report(7))
            self.month_text.setText(self.parent.get_period_report(30))

    def showEvent(self, event):
        self.update_reports()
        super().showEvent(event)


class ProjectListWidget(QWidget):
    """Кастомный виджет для отображения проектов с поиском и недавними"""

    projectSelected = pyqtSignal(str)  # Сигнал при выборе проекта

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.all_projects = []  # Все проекты
        self.recent_projects = []  # Недавние проекты (макс 5)
        self.filtered_projects = []  # Отфильтрованные проекты
        self.is_visible = True  # Состояние видимости

        self.initUI()

    def initUI(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок с кнопкой сворачивания
        header_layout = QHBoxLayout()

        self.toggle_btn = QPushButton("▼ Проекты\задачи")
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                padding: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self.toggle_visibility)
        header_layout.addWidget(self.toggle_btn)

        self.main_layout.addLayout(header_layout)

        # Контейнер для содержимого (будем скрывать/показывать)
        self.content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(5)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Поле поиска
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск проекта...")
        self.search_input.textChanged.connect(self.filter_projects)
        self.search_input.returnPressed.connect(self.select_first_project)
        search_layout.addWidget(self.search_input)
        content_layout.addLayout(search_layout)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        content_layout.addWidget(line)

        # Секция "Недавние"
        self.recent_label = QLabel("⭐ НЕДАВНИЕ")
        self.recent_label.setStyleSheet("font-weight: bold; color: #666;")
        content_layout.addWidget(self.recent_label)

        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(100)
        self.recent_list.itemClicked.connect(self.on_recent_item_clicked)
        content_layout.addWidget(self.recent_list)

        # Секция "Все проекты"
        self.all_label = QLabel("📋 ВСЕ ПРОЕКТЫ\ЗАДАЧИ")
        self.all_label.setStyleSheet("font-weight: bold; color: #666;")
        content_layout.addWidget(self.all_label)

        self.projects_list = QListWidget()
        self.projects_list.itemClicked.connect(self.on_project_item_clicked)
        content_layout.addWidget(self.projects_list)

        self.content_widget.setLayout(content_layout)
        self.main_layout.addWidget(self.content_widget)

        self.setLayout(self.main_layout)

        # Скрываем секцию недавних, если она пуста
        self.update_visibility()

    def toggle_visibility(self):
        """Скрывает или показывает содержимое"""
        self.is_visible = not self.is_visible

        if self.is_visible:
            self.content_widget.show()
            self.toggle_btn.setText("▼ Проекты\задачи")
        else:
            self.content_widget.hide()
            self.toggle_btn.setText("▶ Проекты\задачи")

        # Обновляем размер окна родителя
        if self.parent and hasattr(self.parent, 'adjust_size'):
            self.parent.adjust_size()

    def update_projects(self, all_projects, current_project=None):
        """Обновляет списки проектов"""
        self.all_projects = sorted(all_projects)

        # Обновляем недавние проекты (берем из родителя)
        if hasattr(self.parent, 'recent_projects'):
            self.recent_projects = self.parent.recent_projects[-5:]  # Последние 5

        # Обновляем отображение
        self.filter_projects()

        # Подсвечиваем текущий проект
        if current_project:
            self.highlight_current_project(current_project)

    def filter_projects(self):
        """Фильтрует проекты по поисковому запросу"""
        search_text = self.search_input.text().lower()

        if search_text:
            # Если есть поиск, показываем только отфильтрованные проекты
            self.filtered_projects = [p for p in self.all_projects if search_text in p.lower()]
            self.show_filtered_projects()
        else:
            # Если нет поиска, показываем обычный список
            self.show_all_projects()

        self.update_visibility()

    def show_all_projects(self):
        """Показывает все проекты с разделением на недавние и остальные"""
        # Обновляем недавние проекты
        self.recent_list.clear()
        for project in self.recent_projects:
            if project in self.all_projects:  # Проверяем, что проект еще существует
                item = QListWidgetItem(f"⭐ {project}")
                item.setData(Qt.UserRole, project)
                self.recent_list.addItem(item)

        # Обновляем все проекты (исключая недавние)
        self.projects_list.clear()
        for project in self.all_projects:
            if project not in self.recent_projects:
                item = QListWidgetItem(f"📁 {project}")
                item.setData(Qt.UserRole, project)
                self.projects_list.addItem(item)

    def show_filtered_projects(self):
        """Показывает только отфильтрованные проекты (без разделения)"""
        self.recent_list.clear()
        self.projects_list.clear()

        for project in self.filtered_projects:
            # Добавляем все в основной список
            item = QListWidgetItem(f"📁 {project}")
            item.setData(Qt.UserRole, project)
            self.projects_list.addItem(item)

    def update_visibility(self):
        """Показывает/скрывает секции в зависимости от наличия элементов"""
        has_search = bool(self.search_input.text())

        if has_search:
            # При поиске показываем только секцию всех проектов
            self.recent_label.hide()
            self.recent_list.hide()
            self.all_label.setText("📋 РЕЗУЛЬТАТЫ ПОИСКА")
        else:
            # Без поиска показываем всё
            self.all_label.setText("📋 ВСЕ ПРОЕКТЫ")

            # Показываем недавние, только если они есть
            if self.recent_projects:
                self.recent_label.show()
                self.recent_list.show()
            else:
                self.recent_label.hide()
                self.recent_list.hide()

    def on_recent_item_clicked(self, item):
        """Обработчик клика по недавнему проекту"""
        project = item.data(Qt.UserRole)
        self.projectSelected.emit(project)

    def on_project_item_clicked(self, item):
        """Обработчик клика по проекту из списка"""
        project = item.data(Qt.UserRole)
        self.projectSelected.emit(project)

    def select_first_project(self):
        """Выбирает первый проект в списке (при нажатии Enter в поиске)"""
        if self.projects_list.count() > 0:
            self.projects_list.setCurrentRow(0)
            item = self.projects_list.item(0)
            self.on_project_item_clicked(item)

    def highlight_current_project(self, project_name):
        """Подсвечивает текущий проект в списках"""
        # Снимаем выделение со всех
        self.recent_list.clearSelection()
        self.projects_list.clearSelection()

        # Ищем в недавних
        for i in range(self.recent_list.count()):
            item = self.recent_list.item(i)
            if item.data(Qt.UserRole) == project_name:
                item.setSelected(True)
                self.recent_list.scrollToItem(item)
                return

        # Ищем в основном списке
        for i in range(self.projects_list.count()):
            item = self.projects_list.item(i)
            if item.data(Qt.UserRole) == project_name:
                item.setSelected(True)
                self.projects_list.scrollToItem(item)
                return


class TimeTracker(QWidget):
    def __init__(self):
        super().__init__()
        self.projects = {}  # Словарь: имя проекта -> словарь с данными по дням
        self.current_project = None
        self.timer_running = False
        self.start_time = None  # Время запуска таймера
        self.current_session_project = None  # Проект текущей сессии
        self.statistics_dialog = None  # Окно статистики
        self.block_project_switch = False  # Блокировка рекурсивных вызовов
        self.recent_projects = []  # Список недавних проектов (макс 5)

        # Загрузка данных из файла
        self.load_data()

        self.initUI()

    def initUI(self):
        self.setWindowTitle('⏱ Time Tracker')
        self.setGeometry(300, 300, 320, 200)  # Начальный размер (свернутый список)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)

        # Основной layout
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # Верхняя панель с кнопками управления проектами
        top_layout = QHBoxLayout()
        top_layout.setSpacing(3)

        # Кнопка добавления проекта
        self.add_btn = QPushButton('➕ Добавить проект')
        self.add_btn.setMaximumHeight(25)
        self.add_btn.clicked.connect(self.add_project_dialog)
        top_layout.addWidget(self.add_btn)

        # Кнопка удаления проекта
        self.delete_btn = QPushButton('✖ Удалить')
        self.delete_btn.setMaximumHeight(25)
        self.delete_btn.clicked.connect(self.delete_project_dialog)
        self.delete_btn.setEnabled(False)
        top_layout.addWidget(self.delete_btn)

        layout.addLayout(top_layout)

        # Таймер
        self.time_label = QLabel('00:00:00')
        self.time_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(32)
        font.setBold(True)
        self.time_label.setFont(font)
        layout.addWidget(self.time_label)

        # Кнопки управления таймером
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)

        self.start_pause_btn = QPushButton('▶ Старт')
        self.start_pause_btn.setMaximumHeight(30)
        self.start_pause_btn.clicked.connect(self.start_pause_timer)
        buttons_layout.addWidget(self.start_pause_btn)

        self.report_btn = QPushButton('📅 Отчет')
        self.report_btn.setMaximumHeight(30)
        self.report_btn.clicked.connect(self.show_statistics_dialog)
        buttons_layout.addWidget(self.report_btn)

        layout.addLayout(buttons_layout)

        # Список проектов с поиском (сворачиваемый)
        self.project_list = ProjectListWidget(self)
        self.project_list.projectSelected.connect(self.switch_project_by_name)
        layout.addWidget(self.project_list)

        self.setLayout(layout)

        # Обновляем список проектов
        self.update_project_list()

        # Если есть проекты, выбираем первый
        if self.projects:
            first_project = sorted(self.projects.keys())[0]
            self.current_project = first_project
            self.add_to_recent(first_project)
            self.delete_btn.setEnabled(True)

        # Таймер для обновления времени
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_time_display)
        self.display_timer.start(1000)

        # Системный трей
        self.setup_tray()

        # Сохраняем данные каждые 30 секунд
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.save_data)
        self.auto_save_timer.start(30000)

    def adjust_size(self):
        """Подгоняет размер окна под содержимое"""
        if self.project_list.is_visible:
            # Полный размер
            self.setFixedHeight(450)
        else:
            # Свернутый размер
            self.setFixedHeight(200)

        # Обновляем геометрию
        self.adjustSize()

    def setup_tray(self):
        """Настройка системного трея"""
        self.tray_icon = QSystemTrayIcon(self)

        # Пробуем загрузить иконку
        icon_paths = ['icon.png', 'icon.ico']
        icon_loaded = False
        for path in icon_paths:
            if os.path.exists(path):
                self.tray_icon.setIcon(QIcon(path))
                icon_loaded = True
                break

        if not icon_loaded:
            self.tray_icon.setIcon(self.style().standardIcon(4))

        # Создаем меню трея
        tray_menu = QMenu()

        show_action = tray_menu.addAction("Показать")
        show_action.triggered.connect(self.show)

        report_action = tray_menu.addAction("📅 Отчет")
        report_action.triggered.connect(self.show_statistics_dialog)

        tray_menu.addSeparator()

        # Меню проектов
        self.project_menu = tray_menu.addMenu("Переключить проект")
        self.update_project_menu()

        # Меню удаления
        self.delete_menu = tray_menu.addMenu("✖ Удалить проект")
        self.update_delete_menu()

        tray_menu.addSeparator()

        # Кнопка показать/скрыть проекты
        toggle_action = tray_menu.addAction("📋 Показать список проектов")
        toggle_action.triggered.connect(self.toggle_project_list)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("Выход")
        quit_action.triggered.connect(self.quit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        self.tray_icon.activated.connect(self.tray_icon_activated)

    def toggle_project_list(self):
        """Показывает или скрывает список проектов"""
        self.project_list.toggle_visibility()

        # Обновляем пункт меню
        if self.project_list.is_visible:
            action_text = "📋 Скрыть список проектов"
        else:
            action_text = "📋 Показать список проектов"

        # Обновляем меню (просто для информации, текст в меню не меняем динамически)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def update_project_menu(self):
        if hasattr(self, 'project_menu'):
            self.project_menu.clear()
            for project in sorted(self.projects.keys()):
                action = self.project_menu.addAction(project)
                action.triggered.connect(lambda checked, p=project: self.switch_project_from_menu(p))

    def update_delete_menu(self):
        if hasattr(self, 'delete_menu'):
            self.delete_menu.clear()
            for project in sorted(self.projects.keys()):
                action = self.delete_menu.addAction(project)
                action.triggered.connect(lambda checked, p=project: self.delete_specific_project(p))

    def switch_project_from_menu(self, project_name):
        self.switch_project_by_name(project_name)

    # --- Управление проектами ---
    def add_project_dialog(self):
        name, ok = QInputDialog.getText(self, 'Новый проект', 'Введите название проекта:')
        if ok and name:
            name = name.strip()
            if name:
                if name not in self.projects:
                    self.projects[name] = {}
                    self.update_project_list()
                    self.switch_project_by_name(name)
                    self.update_project_menu()
                    self.update_delete_menu()
                    self.delete_btn.setEnabled(True)
                    self.save_data()

                    self.tray_icon.showMessage(
                        "Time Tracker",
                        f"Проект '{name}' добавлен",
                        QSystemTrayIcon.Information,
                        1500
                    )
                else:
                    QMessageBox.warning(self, 'Ошибка', 'Проект с таким названием уже существует!')

    def delete_project_dialog(self):
        if not self.current_project:
            return
        self.delete_specific_project(self.current_project)

    def delete_specific_project(self, project_name):
        # Проверяем, есть ли в проекте время
        has_time = False
        for date_str, seconds in self.projects[project_name].items():
            if seconds > 0:
                has_time = True
                break

        other_projects = [p for p in self.projects.keys() if p != project_name]

        if not other_projects and has_time:
            reply = QMessageBox.question(
                self, 'Подтверждение',
                f"Проект '{project_name}' содержит время, но это единственный проект.\n"
                "Удалить проект и всё время?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.timer_running and self.current_session_project == project_name:
                    self.save_current_session()

                del self.projects[project_name]
                self.after_project_deletion(project_name)
            return

        dialog = DeleteProjectDialog(project_name, has_time, other_projects, self)
        if dialog.exec_() == QDialog.Accepted:
            action, target_project = dialog.get_action()

            if self.timer_running and self.current_session_project == project_name:
                self.save_current_session()

            if action == 'delete':
                del self.projects[project_name]
                self.after_project_deletion(project_name)

                self.tray_icon.showMessage(
                    "Time Tracker",
                    f"Проект '{project_name}' удален",
                    QSystemTrayIcon.Information,
                    1500
                )

            elif action == 'transfer' and target_project:
                for date_str, seconds in self.projects[project_name].items():
                    if seconds > 0:
                        if date_str not in self.projects[target_project]:
                            self.projects[target_project][date_str] = 0
                        self.projects[target_project][date_str] += seconds

                del self.projects[project_name]
                self.after_project_deletion(project_name, switch_to=target_project)

                self.tray_icon.showMessage(
                    "Time Tracker",
                    f"Проект '{project_name}' удален, время перенесено в '{target_project}'",
                    QSystemTrayIcon.Information,
                    2000
                )

            self.save_data()

    def after_project_deletion(self, deleted_project, switch_to=None):
        if self.current_project == deleted_project:
            if switch_to and switch_to in self.projects:
                self.current_project = switch_to
            elif self.projects:
                self.current_project = sorted(self.projects.keys())[0]
            else:
                self.current_project = None
                self.delete_btn.setEnabled(False)

                if self.timer_running:
                    self.timer_running = False
                    self.start_pause_btn.setText('▶ Старт')
                    self.start_time = None
                    self.current_session_project = None

        # Удаляем из недавних, если был там
        if deleted_project in self.recent_projects:
            self.recent_projects.remove(deleted_project)

        self.update_project_list()
        self.update_project_menu()
        self.update_delete_menu()

        if self.current_project:
            self.project_list.highlight_current_project(self.current_project)

    def update_project_list(self):
        """Обновляет список проектов в виджете"""
        self.project_list.update_projects(
            list(self.projects.keys()),
            self.current_project
        )
        self.delete_btn.setEnabled(len(self.projects) > 0)

    def add_to_recent(self, project_name):
        """Добавляет проект в список недавних"""
        if project_name in self.recent_projects:
            self.recent_projects.remove(project_name)
        self.recent_projects.append(project_name)
        # Оставляем только последние 5
        if len(self.recent_projects) > 5:
            self.recent_projects = self.recent_projects[-5:]

    # --- Переключение проектов ---
    def switch_project_by_name(self, project_name):
        """Переключение на проект по имени"""
        if self.block_project_switch or not project_name or project_name == self.current_project:
            return

        # Добавляем в недавние
        self.add_to_recent(project_name)

        # Если таймер запущен, сохраняем время на текущий проект
        if self.timer_running and self.current_session_project:
            self.save_current_session()

            # Начинаем новую сессию на новом проекте
            self.start_time = QDateTime.currentDateTime().toSecsSinceEpoch()
            self.current_session_project = project_name

            self.tray_icon.showMessage(
                "Time Tracker",
                f"Переключено на проект: {project_name}",
                QSystemTrayIcon.Information,
                1000
            )

        # Обновляем текущий проект
        self.current_project = project_name

        # Обновляем выделение в списке
        self.project_list.highlight_current_project(project_name)

        # Обновляем список проектов (для обновления недавних)
        self.update_project_list()

    def save_current_session(self):
        """Сохраняет текущую сессию в статистику"""
        if self.start_time and self.current_session_project:
            elapsed = int((QDateTime.currentDateTime().toSecsSinceEpoch() - self.start_time))
            if elapsed > 0:
                today = date.today().isoformat()
                if today not in self.projects[self.current_session_project]:
                    self.projects[self.current_session_project][today] = 0
                self.projects[self.current_session_project][today] += elapsed
                self.save_data()

    # --- Логика таймера ---
    def start_pause_timer(self):
        if not self.current_project:
            QMessageBox.warning(self, 'Ошибка', 'Сначала создайте или выберите проект!')
            return

        if self.timer_running:
            # Пауза
            self.timer_running = False
            self.start_pause_btn.setText('▶ Старт')

            self.save_current_session()

            self.start_time = None
            self.current_session_project = None

            self.tray_icon.showMessage(
                "Time Tracker",
                "Таймер на паузе",
                QSystemTrayIcon.Information,
                1000
            )
        else:
            # Старт
            self.timer_running = True
            self.start_time = QDateTime.currentDateTime().toSecsSinceEpoch()
            self.current_session_project = self.current_project
            self.start_pause_btn.setText('⏸ Пауза')

            self.tray_icon.showMessage(
                "Time Tracker",
                f"Работа над проектом: {self.current_project}",
                QSystemTrayIcon.Information,
                1000
            )

    def update_time_display(self):
        """Обновляет отображение общего времени"""
        total_seconds = 0

        today = date.today().isoformat()
        for project, days in self.projects.items():
            if today in days:
                total_seconds += days[today]

        if self.timer_running and self.start_time and self.current_session_project:
            current_session = int((QDateTime.currentDateTime().toSecsSinceEpoch() - self.start_time))
            total_seconds += current_session

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        self.time_label.setText(f'{hours:02d}:{minutes:02d}:{seconds:02d}')

        if self.statistics_dialog and self.statistics_dialog.isVisible():
            self.statistics_dialog.update_reports()

    # --- Статистика и отчеты ---
    def show_statistics_dialog(self):
        if not self.statistics_dialog:
            self.statistics_dialog = StatisticsDialog(self)

        if self.statistics_dialog.isVisible():
            self.statistics_dialog.raise_()
            self.statistics_dialog.activateWindow()
        else:
            self.statistics_dialog.show()

    def get_today_report(self):
        today = date.today().isoformat()
        report = "📅 ОТЧЕТ ЗА СЕГОДНЯ\n"
        report += "=" * 50 + "\n\n"

        total_seconds = 0
        projects_data = []

        for project in sorted(self.projects.keys()):
            if today in self.projects[project]:
                seconds = self.projects[project][today]
                total_seconds += seconds
                projects_data.append((project, seconds, False))

        current_session_seconds = 0
        if self.timer_running and self.start_time and self.current_session_project:
            current_session_seconds = int((QDateTime.currentDateTime().toSecsSinceEpoch() - self.start_time))

            found = False
            for i, (p, s, is_current) in enumerate(projects_data):
                if p == self.current_session_project:
                    projects_data[i] = (p, s + current_session_seconds, True)
                    found = True
                    break

            if not found and current_session_seconds > 0:
                projects_data.append((self.current_session_project, current_session_seconds, True))

        if projects_data:
            for project, seconds, is_current in projects_data:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                current_mark = " (текущая сессия)" if is_current else ""
                report += f"• {project}: {hours:02d}:{minutes:02d} ч{current_mark}\n"

            if current_session_seconds > 0:
                session_accounted = any(is_current for _, _, is_current in projects_data)
                if not session_accounted:
                    total_seconds += current_session_seconds

            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            report += f"\n✨ ВСЕГО: {hours:02d}:{minutes:02d} ч"
        else:
            report += "Нет данных за сегодня"

        if self.timer_running and self.current_project:
            report += f"\n\n⏱ Текущий проект: {self.current_project}"

        now = QDateTime.currentDateTime().toString("hh:mm:ss")
        report += f"\n\nОбновлено: {now}"

        return report

    def get_period_report(self, days):
        period = "неделю" if days == 7 else "месяц"
        report = f"📊 СТАТИСТИКА ЗА {period.upper()}\n"
        report += "=" * 50 + "\n\n"

        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        report += f"Период: {start_date} - {end_date}\n"
        report += "-" * 50 + "\n\n"

        total_all = 0
        for project in sorted(self.projects.keys()):
            project_total = 0
            report += f"📁 {project}\n"

            current_date = start_date
            has_data = False

            while current_date <= end_date:
                date_str = current_date.isoformat()
                if date_str in self.projects[project]:
                    seconds = self.projects[project][date_str]
                    project_total += seconds
                    total_all += seconds
                    hours = seconds // 3600
                    minutes = (seconds % 3600) // 60
                    date_formatted = current_date.strftime("%d.%m.%Y")
                    report += f"  {date_formatted}: {hours:02d}:{minutes:02d} ч\n"
                    has_data = True
                current_date += timedelta(days=1)

            if has_data:
                hours = project_total // 3600
                minutes = (project_total % 3600) // 60
                report += f"  ➤ Итого: {hours:02d}:{minutes:02d} ч\n\n"
            else:
                report += "  Нет данных\n\n"

        if total_all > 0:
            report += "=" * 50 + "\n"
            hours = total_all // 3600
            minutes = (total_all % 3600) // 60
            report += f"🏆 ВСЕГО ЗА ПЕРИОД: {hours:02d}:{minutes:02d} ч"

        return report

    # --- Работа с файлами ---
    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    self.projects = json.load(f)
            except:
                self.projects = {}
        else:
            self.projects = {}

    def save_data(self):
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.projects, f, indent=2, ensure_ascii=False)
        except:
            pass

    def closeEvent(self, event):
        self.save_current_session()
        self.save_data()
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Time Tracker",
            "Программа свернута в трей",
            QSystemTrayIcon.Information,
            1500
        )

    def quit_app(self):
        self.save_current_session()

        if self.statistics_dialog:
            self.statistics_dialog.close()

        self.save_data()
        QApplication.quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    ex = TimeTracker()
    ex.show()
    sys.exit(app.exec_())