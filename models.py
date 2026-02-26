import json
import os
from datetime import datetime
from config import get_data_path


class ProjectModel:
    """Модель для работы с проектами"""

    def __init__(self):
        self.projects = {}
        self.current_project = None
        self.current_object = None
        self.data_file = get_data_path()

    def load_data(self):
        """Загружает данные из файла"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.projects = json.load(f)
            except Exception:
                self.projects = {}
        return self.projects

    def save_data(self):
        """Сохраняет данные в файл"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.projects, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            return False

    def add_project(self, name, version, template):
        """Добавляет новый проект"""
        if name not in self.projects:
            self.projects[name] = {
                "version": version,
                "template": template,
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "objects": {},
                "checklists": {}
            }
            return True
        return False

    def add_object(self, project_name, object_name):
        """Добавляет объект к проекту"""
        if project_name in self.projects and object_name not in self.projects[project_name]["objects"]:
            self.projects[project_name]["objects"][object_name] = {
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "checklists": {}
            }
            return True
        return False

    def delete_project(self, project_name):
        """Удаляет проект"""
        if project_name in self.projects:
            del self.projects[project_name]
            return True
        return False

    def delete_object(self, project_name, object_name):
        """Удаляет объект"""
        if project_name in self.projects and object_name in self.projects[project_name]["objects"]:
            del self.projects[project_name]["objects"][object_name]
            return True
        return False

    def rename_project(self, old_name, new_name):
        """Переименовывает проект"""
        if old_name in self.projects and new_name not in self.projects:
            self.projects[new_name] = self.projects.pop(old_name)
            return True
        return False

    def rename_object(self, project_name, old_name, new_name):
        """Переименовывает объект"""
        if (project_name in self.projects and
                old_name in self.projects[project_name]["objects"] and
                new_name not in self.projects[project_name]["objects"]):
            self.projects[project_name]["objects"][new_name] = \
                self.projects[project_name]["objects"].pop(old_name)
            return True
        return False

    def get_project_template(self, project_name):
        """Возвращает шаблон проекта"""
        return self.projects.get(project_name, {}).get("template", "Основной_чеклист.txt")

    def get_project_version(self, project_name):
        """Возвращает версию проекта"""
        return self.projects.get(project_name, {}).get("version", "—")

    def update_project_template(self, project_name, template_name):
        """Обновляет шаблон проекта"""
        if project_name in self.projects:
            self.projects[project_name]["template"] = template_name
            return True
        return False

    def init_project_checklists(self, project_name, template_data):
        """Инициализирует чек-листы проекта"""
        if project_name in self.projects:
            self.projects[project_name]["checklists"] = {}
            for tab_name, items in template_data.items():
                if tab_name != "Генплан":
                    self.projects[project_name]["checklists"][tab_name] = {}
                    for item in items:
                        self.projects[project_name]["checklists"][tab_name][item] = {
                            "status": 0,
                            "comment": None
                        }
            return True
        return False

    def init_object_checklists(self, project_name, object_name, template_data):
        """Инициализирует чек-листы объекта"""
        if (project_name in self.projects and
                object_name in self.projects[project_name]["objects"] and
                "Генплан" in template_data):
            self.projects[project_name]["objects"][object_name]["checklists"] = {}
            for item in template_data["Генплан"]:
                self.projects[project_name]["objects"][object_name]["checklists"][item] = {
                    "status": 0,
                    "comment": None
                }
            return True
        return False

    def save_project_item_status(self, project_name, tab_name, item, status, comment):
        """Сохраняет статус пункта проекта"""
        if project_name in self.projects:
            if tab_name not in self.projects[project_name]["checklists"]:
                self.projects[project_name]["checklists"][tab_name] = {}
            if item not in self.projects[project_name]["checklists"][tab_name]:
                self.projects[project_name]["checklists"][tab_name][item] = {}
            self.projects[project_name]["checklists"][tab_name][item] = {
                "status": status,
                "comment": comment
            }
            return True
        return False

    def save_object_item_status(self, project_name, object_name, item, status, comment):
        """Сохраняет статус пункта объекта"""
        if (project_name in self.projects and
                object_name in self.projects[project_name]["objects"]):
            if item not in self.projects[project_name]["objects"][object_name]["checklists"]:
                self.projects[project_name]["objects"][object_name]["checklists"][item] = {}
            self.projects[project_name]["objects"][object_name]["checklists"][item] = {
                "status": status,
                "comment": comment
            }
            return True
        return False

    def get_project_item_status(self, project_name, tab_name, item):
        """Возвращает статус пункта проекта"""
        try:
            return (self.projects[project_name]["checklists"][tab_name][item]["status"],
                    self.projects[project_name]["checklists"][tab_name][item]["comment"])
        except:
            return (0, None)

    def get_object_item_status(self, project_name, object_name, item):
        """Возвращает статус пункта объекта"""
        try:
            return (self.projects[project_name]["objects"][object_name]["checklists"][item]["status"],
                    self.projects[project_name]["objects"][object_name]["checklists"][item]["comment"])
        except:
            return (0, None)