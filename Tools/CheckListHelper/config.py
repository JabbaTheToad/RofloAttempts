import os


# Конфигурация приложения
class Config:
    APP_TITLE = "Тестирование проектов - Чек-лист"
    APP_GEOMETRY = "1600x900"
    DATA_FILE = "projects_data.json"
    TEMPLATES_DIR = "checklist_templates"
    EXPORTS_DIR = "exports"

    # Цвета для статусов
    COLORS = {
        "done": "#4CAF50",  # Зеленый
        "bug": "#F44336",  # Красный
        "none": "#FFFFFF",  # Белый
        "selected": "#E3F2FD"  # Голубой для выделения
    }

    # Настройки интерфейса
    CHECKLIST_ITEM_WIDTH = 40
    CANVAS_HEIGHT = 400
    TREE_COLUMN_WIDTHS = {
        "name": 150,
        "version": 70,
        "template": 100
    }


# Пути к файлам
def get_template_path(filename):
    """Возвращает полный путь к файлу шаблона"""
    return os.path.join(Config.TEMPLATES_DIR, filename)


def get_data_path():
    """Возвращает полный путь к файлу данных"""
    return Config.DATA_FILE


def get_exports_dir():
    """Возвращает путь к директории экспорта"""
    exports_dir = Config.EXPORTS_DIR
    if not os.path.exists(exports_dir):
        os.makedirs(exports_dir)
    return exports_dir