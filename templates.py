import os
import shutil
from config import Config, get_template_path


class TemplateManager:
    """Менеджер шаблонов чек-листов"""

    def __init__(self):
        self.available_templates = {}
        self.templates_dir = Config.TEMPLATES_DIR
        self._ensure_templates_dir()
        self.load_templates()

    def _ensure_templates_dir(self):
        """Создает директорию для шаблонов если её нет"""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            self._create_default_templates()

    def _create_default_templates(self):
        """Создает шаблоны по умолчанию"""
        default_templates = {
            "Основной_чеклист.txt": """Время
- Ползунок/полоска
- Ускорить
- Времена года - Осадки
- Текущее время
- День/ночь

Информация о
- Проекте - Переходы
- Проекте - Кол-во кадров
- Застройщике
- Разработчике

Поиск
- Переход к выбранному объекту
- Проекты
- Количество комнат
- Цена
- Площадь
- Этаж
- Отделка
- Фильтр - Сначала дешевые
- Фильтр - Сначала дороже
- Фильтр - С меньшей площадью
- Фильтр - С большей площадью
- Фильтр - По возрастанию этажа
- Фильтр - По убыванию этажа

Начало сеанса
- Телефон - Имя
- Телефон - Почта
- Телефон - Менеджер
- Избранное

Видеотур
- Цикличность
- Старт/Стоп
- Перемотка
- Повтор

Избранное
- Квартиры - Переход к выбранному объекту
- Квартиры - Добавление/Удаление
- Квартиры - Отправка
- Снимки - Добавление/Удаление
- Снимки - Отправка

Инфраструктура
- Окружение - Образование
- Окружение - Парки и водоемы
- Окружение - Культура и досуг
- Окружение - Торговые центры
- Окружение - Спорт и увлечения
- Окружение - Рестораны и кафе
- Окружение - Гастрономия
- Окружение - Медицина
- Окружение - Красота
- Дистанция - минут/метров
- Транспорт - Метро
- Транспорт - Общественный транспорт
- Транспорт - Велодорожки

Настройки
- Toggle
- Button
- Scroll_Bar

Генплан
- Точки интереса - Корпуса/сектора
- Корпуса/сектора - Этаж
- Этаж - Квартира
- Квартира - Комнатность
- Квартира - Карточка
- Квартира - 3д-тур
- Квартира - Расположение
- Квартира - Аналогичные/похожие
- Квартира - О квартире
- Квартира - Избранное
- Квартира - Бронь
- Квартира - Метка/поинт
- Квартира - Стоимость
- Квартира - Метраж
- Квартира - Похожие
- Квартира - Крышки
- Этаж - Лифт
- Лифт - Кол-во этажей
- Лифт - Работоспособность
- Этаж - Холл
- Этаж - МОП
- Этаж - Крышки
- Этаж - 3д-тур
- Корпуса/сектора - Переход
- Корпуса/сектора - Отображение
- Двор - 3д-тур
- Объекты""",

            "Генплан_детальный.txt": """Генплан
- Корпуса - Отображение на карте
- Корпуса - Кликабельность
- Сектора - Разделение
- Этажи - Навигация
- Квартиры - Отображение на плане
- Квартиры - Выбор
- 3D-тур по территории
- Дворы - Детализация
- Детские площадки
- Парковки
- Ландшафт
- Подсветка территории
- Инфраструктура на карте
- Транспортные узлы
- Пешеходные дорожки"""
        }

        for filename, content in default_templates.items():
            filepath = get_template_path(filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

    def load_templates(self):
        """Загружает доступные шаблоны из txt файлов"""
        self.available_templates = {}
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.txt'):
                filepath = get_template_path(filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.available_templates[filename] = self.parse_template(content)
                except Exception as e:
                    print(f"Ошибка загрузки шаблона {filename}: {e}")
        return self.available_templates

    def parse_template(self, content):
        """Парсит содержимое шаблона в структуру чек-листов"""
        checklists = {}
        current_tab = None

        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue

            if not line.startswith('-'):
                current_tab = line
                checklists[current_tab] = []
            else:
                if current_tab:
                    item = line[1:].strip()
                    checklists[current_tab].append(item)

        return checklists

    def get_template_names(self):
        """Возвращает список названий шаблонов"""
        return list(self.available_templates.keys())

    def get_template_data(self, template_name):
        """Возвращает данные шаблона по имени"""
        return self.available_templates.get(template_name, {})

    def import_template(self, filepath):
        """Импортирует шаблон из файла"""
        try:
            dest_filename = os.path.basename(filepath)
            dest_path = get_template_path(dest_filename)
            shutil.copy2(filepath, dest_path)
            self.load_templates()
            return True, dest_filename
        except Exception as e:
            return False, str(e)

    def save_template(self, filename, content):
        """Сохраняет новый шаблон"""
        if not filename.endswith('.txt'):
            filename += '.txt'

        filepath = get_template_path(filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.load_templates()
            return True, filename
        except Exception as e:
            return False, str(e)

    def get_template_content(self, template_name):
        """Возвращает содержимое шаблона"""
        filepath = get_template_path(template_name)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return True, f.read()
        except Exception as e:
            return False, str(e)