import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Dict, List
import os
import sys
import math

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для диалога
(NAME, LEFT, RIGHT, WIDTH, DOOR_COUNT, DOOR_DATA, CONNECT_ROOM,
 WALL_HEIGHT, MATERIAL_TYPE, SELECT_ROOM_FOR_MATERIAL, 
 LAMINATE_SIZE, SELECT_ROOM_FOR_EDIT, EDIT_OPTION, 
 EDIT_VALUE, SELECT_WALL_FOR_HEIGHT) = range(15)

user_data: Dict[int, Dict] = {}

# --- Функции для рисования ---
def draw_floor_plan(rooms: List[Dict], current_room: Dict = None, highlight_connection: int = None):
    """Рисует общий план всех комнат с дверями и связями между комнатами."""
    try:
        padding = 100
        room_spacing = 50
        
        # Создаем временный список всех комнат
        all_rooms = rooms.copy()
        if current_room and all(k in current_room for k in ['left', 'right', 'width']):
            temp_room = current_room.copy()
            if 'name' not in temp_room:
                temp_room['name'] = 'Новая комната'
            if 'doors' not in temp_room:
                temp_room['doors'] = []
            if 'id' not in temp_room:
                temp_room['id'] = -1  # временный ID
            all_rooms.append(temp_room)
        
        # Рассчитываем размеры изображения
        rooms_per_row = 2
        rows = max(1, (len(all_rooms) + rooms_per_row - 1) // rooms_per_row)
        
        img_width = max(1000, rooms_per_row * 450 + padding * 2)
        img_height = max(800, rows * 400 + padding * 2)
        
        # Создаем изображение
        img = Image.new('RGB', (img_width, img_height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Загружаем шрифт
        font_title = ImageFont.load_default()
        font_room = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_door = ImageFont.load_default()
        
        # Пытаемся загрузить нормальный шрифт
        try:
            font_title = ImageFont.truetype("arial.ttf", 24)
            font_room = ImageFont.truetype("arial.ttf", 20)
            font_label = ImageFont.truetype("arial.ttf", 16)
            font_door = ImageFont.truetype("arial.ttf", 12)
        except:
            pass
        
        # Словарь для хранения координат центров комнат
        room_centers = {}
        room_positions = {}
        
        # Сначала рисуем все комнаты и сохраняем их позиции
        if all_rooms:
            for idx, room in enumerate(all_rooms):
                # Позиция комнаты
                row = idx // rooms_per_row
                col = idx % rooms_per_row
                
                x_offset = padding + col * (450 + room_spacing)
                y_offset = padding + row * (400 + room_spacing)
                
                # Размеры комнаты
                left_wall = room.get('left', 0)
                right_wall = room.get('right', 0)
                width = room.get('width', 0)
                
                if left_wall > 0 and right_wall > 0 and width > 0:
                    # Масштабируем
                    max_dim = max(left_wall, right_wall, width)
                    cell_scale = min(250 / max_dim, 200 / max_dim) if max_dim > 0 else 1
                    
                    # Координаты углов
                    x0 = x_offset + 50
                    y0 = y_offset + 50
                    x1 = x0 + (width * cell_scale)
                    y1_left = y0 + (left_wall * cell_scale)
                    y1_right = y0 + (right_wall * cell_scale)
                    
                    # Сохраняем координаты комнаты
                    room_positions[room.get('id', idx)] = {
                        'x0': x0, 'y0': y0,
                        'x1': x1, 'y1_left': y1_left, 'y1_right': y1_right,
                        'scale': cell_scale,
                        'center': ((x0 + x1) // 2, (y0 + max(y1_left, y1_right)) // 2)
                    }
                    
                    # Рисуем стены
                    # Левая стена
                    draw.line([(x0, y0), (x0, y1_left)], fill='black', width=3)
                    # Правая стена
                    draw.line([(x1, y0), (x1, y1_right)], fill='black', width=3)
                    # Верхняя стена
                    draw.line([(x0, y0), (x1, y0)], fill='black', width=3)
                    # Нижняя стена
                    draw.line([(x0, y1_left), (x1, y1_right)], fill='black', width=3)
                    
                    # Добавляем информацию о высоте стен для обоев
                    if 'wall_height' in room:
                        draw.text((x0 + 10, y0 + 10), f"h={room['wall_height']}м", 
                                 fill='purple', font=font_label)
                    
                    # Рисуем двери и соединения между комнатами
                    doors = room.get('doors', [])
                    for door in doors:
                        wall = door.get('wall', '').lower()
                        door_width = door.get('width', 0.9) * cell_scale
                        door_offset = door.get('offset', 1.0) * cell_scale
                        connects_to = door.get('connects_to')
                        
                        # Определяем координаты двери
                        door_coords = None
                        if wall == 'левая':
                            door_x = x0
                            door_y = y0 + door_offset
                            door_coords = (door_x, door_y)
                            # Рисуем дверь
                            draw.rectangle(
                                [door_x - 4, door_y - door_width/2, door_x + 4, door_y + door_width/2],
                                fill='brown'
                            )
                        elif wall == 'правая':
                            door_x = x1
                            door_y = y0 + door_offset
                            door_coords = (door_x, door_y)
                            draw.rectangle(
                                [door_x - 4, door_y - door_width/2, door_x + 4, door_y + door_width/2],
                                fill='brown'
                            )
                        elif wall == 'верхняя':
                            door_x = x0 + door_offset
                            door_y = y0
                            door_coords = (door_x, door_y)
                            draw.rectangle(
                                [door_x - door_width/2, door_y - 4, door_x + door_width/2, door_y + 4],
                                fill='brown'
                            )
                        elif wall == 'нижняя':
                            door_x = x0 + door_offset
                            door_y = max(y1_left, y1_right)
                            door_coords = (door_x, door_y)
                            draw.rectangle(
                                [door_x - door_width/2, door_y - 4, door_x + door_width/2, door_y + 4],
                                fill='brown'
                            )
                        
                        # Если дверь соединяется с другой комнатой, рисуем линию связи
                        if connects_to is not None and connects_to in room_positions:
                            other_room = room_positions[connects_to]
                            other_center = other_room['center']
                            
                            # Определяем цвет линии (выделяем если это текущее соединение)
                            line_color = 'red' if highlight_connection == connects_to else 'blue'
                            line_width = 3 if highlight_connection == connects_to else 2
                            
                            # Рисуем пунктирную линию между комнатами
                            draw.line([door_coords, other_center], fill=line_color, width=line_width)
                            
                            # Добавляем стрелочку или подпись
                            mid_x = (door_coords[0] + other_center[0]) // 2
                            mid_y = (door_coords[1] + other_center[1]) // 2
                            draw.text((mid_x, mid_y), "🚪", fill='blue', font=font_door)
                        
                        # Подпись ширины двери
                        if door_coords:
                            draw.text(
                                (door_coords[0] - 20, door_coords[1] - 20),
                                f"{door.get('width', 0.9)}м",
                                fill='brown',
                                font=font_door
                            )
                    
                    # Название комнаты
                    room_color = 'blue' if room == current_room else 'green'
                    draw.text((x0, y0 - 30), room.get('name', 'Комната')[:20], 
                             fill=room_color, font=font_room)
                    
                    # Подписи размеров стен
                    draw.text((x0 - 50, (y0 + y1_left) / 2 - 10), f"← {left_wall}м", 
                             fill='gray', font=font_label)
                    draw.text((x1 + 10, (y0 + y1_right) / 2 - 10), f"{right_wall}м →", 
                             fill='gray', font=font_label)
                    draw.text(((x0 + x1) / 2 - 30, y0 - 40), f"↑ {width}м", 
                             fill='gray', font=font_label)
                    
                    # Площадь
                    area = ((left_wall + right_wall) / 2) * width
                    draw.text((x0, max(y1_left, y1_right) + 30), f"S={area:.1f}м²", 
                             fill='red', font=font_label)
        
        # Статистика
        total_area = 0
        total_doors = 0
        connections = 0
        for room in rooms:
            if all(k in room for k in ['left', 'right', 'width']):
                total_area += ((room['left'] + room['right']) / 2) * room['width']
                room_doors = room.get('doors', [])
                total_doors += len(room_doors)
                connections += sum(1 for d in room_doors if d.get('connects_to') is not None)
        
        draw.text((20, img_height - 80), f"Общая площадь: {total_area:.2f} м²", 
                  fill='darkred', font=font_title)
        draw.text((20, img_height - 55), f"Всего дверей: {total_doors}", 
                  fill='brown', font=font_label)
        draw.text((20, img_height - 30), f"Соединений между комнатами: {connections//2}", 
                  fill='blue', font=font_label)
        
        # Сохраняем
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio
        
    except Exception as e:
        logger.error(f"Ошибка при рисовании: {e}")
        img = Image.new('RGB', (400, 200), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), f"Ошибка создания плана", fill='red')
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio

# --- Функции для расчёта материалов ---
def calculate_wallpaper(room: Dict, wall_height: float = None) -> Dict:
    """Рассчитывает необходимое количество рулонов обоев."""
    if not room:
        return {'error': 'Комната не найдена'}
    
    # Используем сохранённую высоту стен или переданную
    height = wall_height or room.get('wall_height')
    if not height:
        return {'error': 'Не указана высота стен'}
    
    # Периметр комнаты (сумма всех стен)
    perimeter = room['left'] + room['right'] + 2 * room['width']
    
    # Вычитаем дверные проёмы
    doors_width = 0
    for door in room.get('doors', []):
        doors_width += door.get('width', 0)
    
    # Площадь оклейки
    wall_area = (perimeter - doors_width) * height
    
    # Стандартный рулон обоев (10м x 0.53м)
    roll_area = 10 * 0.53  # 5.3 м²
    
    # Количество рулонов (округляем вверх)
    rolls = math.ceil(wall_area / roll_area)
    
    # Добавляем запас 10% на подгонку рисунка
    rolls_with_margin = math.ceil(rolls * 1.1)
    
    return {
        'wall_area': round(wall_area, 2),
        'rolls_needed': rolls,
        'rolls_with_margin': rolls_with_margin,
        'perimeter': round(perimeter, 2),
        'height': height
    }

def calculate_laminate(room: Dict, plank_length: float, plank_width: float) -> Dict:
    """Рассчитывает необходимое количество ламината."""
    if not room:
        return {'error': 'Комната не найдена'}
    
    # Площадь комнаты
    room_area = ((room['left'] + room['right']) / 2) * room['width']
    
    # Площадь одной доски
    plank_area = plank_length * plank_width
    
    # Количество досок
    planks_needed = math.ceil(room_area / plank_area)
    
    # Добавляем запас на подрезку (7% для прямой укладки, 10% для диагональной)
    planks_with_margin_straight = math.ceil(planks_needed * 1.07)
    planks_with_margin_diagonal = math.ceil(planks_needed * 1.10)
    
    # Количество упаковок (обычно в упаковке 8-10 досок)
    packs_size = 8  # среднее количество в упаковке
    packs_needed = math.ceil(planks_with_margin_straight / packs_size)
    
    return {
        'room_area': round(room_area, 2),
        'planks_needed': planks_needed,
        'planks_with_margin_straight': planks_with_margin_straight,
        'planks_with_margin_diagonal': planks_with_margin_diagonal,
        'packs_needed': packs_needed,
        'plank_area': round(plank_area, 3)
    }

# --- Функция для создания меню ---
def get_main_keyboard():
    """Возвращает основную клавиатуру меню."""
    keyboard = [
        ['➕ Добавить комнату'],
        ['📋 Список комнат', '📊 Общий план'],
        ['🧮 Расчёт материалов', '✏️ Редактировать комнату'],
        ['🔗 Схема соединений', '❌ Очистить всё']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_walls_keyboard():
    """Клавиатура для выбора стены."""
    keyboard = [
        ['Левая', 'Правая', 'Верхняя', 'Нижняя'],
        ['❌ Закончить добавление дверей']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_rooms_keyboard(rooms: List[Dict], current_room_id: int = None):
    """Клавиатура для выбора комнаты."""
    keyboard = []
    for room in rooms:
        if current_room_id is None or room.get('id') != current_room_id:
            keyboard.append([f"{room['name']} (ID: {room['id']})"])
    keyboard.append(['❌ Отмена'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_material_type_keyboard():
    """Клавиатура для выбора типа материала."""
    keyboard = [
        ['🧱 Обои (стены)'],
        ['🪵 Ламинат (пол)'],
        ['❌ Отмена']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_edit_options_keyboard():
    """Клавиатура для выбора параметра редактирования."""
    keyboard = [
        ['📏 Размеры стен'],
        ['📐 Ширину комнаты'],
        ['🧱 Высоту стен'],
        ['🚪 Двери'],
        ['❌ Отмена']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало работы с ботом."""
    user_id = update.effective_user.id
    
    # Инициализируем данные пользователя
    if user_id not in user_data:
        user_data[user_id] = {'rooms': [], 'next_room_id': 0}
    
    await update.message.reply_text(
        '🏠 Добро пожаловать в помощник по ремонту!\n'
        'Я помогу тебе создать план всех помещений, соединить их через дверные проёмы,\n'
        'и рассчитать необходимое количество материалов для ремонта.\n\n'
        'Выбери действие:',
        reply_markup=get_main_keyboard()
    )

# --- Обработчики для добавления комнаты (как в вашем коде) ---
async def add_room_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса добавления комнаты."""
    await update.message.reply_text(
        'Введите название комнаты (например, "Гостиная"):'
    )
    return NAME

async def add_room_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем название комнаты."""
    user_id = update.effective_user.id
    room_name = update.message.text
    
    if len(room_name) > 50:
        await update.message.reply_text('Название слишком длинное. Придумайте покороче (макс 50 символов):')
        return NAME
    
    # Сохраняем название во временные данные
    if 'temp_room' not in user_data[user_id]:
        user_data[user_id]['temp_room'] = {}
    
    # Назначаем ID для новой комнаты
    user_data[user_id]['temp_room']['id'] = user_data[user_id]['next_room_id']
    user_data[user_id]['temp_room']['name'] = room_name
    user_data[user_id]['temp_room']['doors'] = []
    
    await update.message.reply_text(
        f'Комната "{room_name}".\n'
        'Введите длину ЛЕВОЙ стены в метрах:'
    )
    return LEFT

async def add_room_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем левую стену."""
    user_id = update.effective_user.id
    try:
        value = float(update.message.text.replace(',', '.'))
        if value <= 0 or value > 50:
            await update.message.reply_text('Длина стены должна быть положительной и не больше 50 метров:')
            return LEFT
            
        user_data[user_id]['temp_room']['left'] = value
        await update.message.reply_text(f'Левая стена: {value}м. Теперь введите длину ПРАВОЙ стены:')
        return RIGHT
    except ValueError:
        await update.message.reply_text('❌ Пожалуйста, введите число (например, 3.5)')
        return LEFT

async def add_room_right(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем правую стену."""
    user_id = update.effective_user.id
    try:
        value = float(update.message.text.replace(',', '.'))
        if value <= 0 or value > 50:
            await update.message.reply_text('Длина стены должна быть положительной и не больше 50 метров:')
            return RIGHT
            
        user_data[user_id]['temp_room']['right'] = value
        await update.message.reply_text(
            f'Правая стена: {value}м.\n'
            'Теперь введите расстояние между стенами (ширину):'
        )
        return WIDTH
    except ValueError:
        await update.message.reply_text('❌ Пожалуйста, введите число.')
        return RIGHT

async def add_room_width(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем ширину и переходим к дверям."""
    user_id = update.effective_user.id
    try:
        width_val = float(update.message.text.replace(',', '.'))
        if width_val <= 0 or width_val > 50:
            await update.message.reply_text('Ширина должна быть положительной и не больше 50 метров:')
            return WIDTH
            
        user_data[user_id]['temp_room']['width'] = width_val
        
        # Спрашиваем про двери
        await update.message.reply_text(
            f'✅ Размеры комнаты "{user_data[user_id]["temp_room"]["name"]}" сохранены.\n\n'
            'Сколько входов/дверей в этой комнате? (введите число от 0 до 10)'
        )
        return DOOR_COUNT
        
    except ValueError:
        await update.message.reply_text('❌ Пожалуйста, введите число.')
        return WIDTH

async def add_room_door_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем количество дверей."""
    user_id = update.effective_user.id
    try:
        count = int(update.message.text)
        if count < 0 or count > 10:
            await update.message.reply_text('Пожалуйста, введите число от 0 до 10:')
            return DOOR_COUNT
        
        # Сохраняем количество дверей и начинаем сбор данных о каждой
        user_data[user_id]['temp_room']['door_count'] = count
        user_data[user_id]['temp_room']['current_door'] = 0
        
        if count == 0:
            # Если дверей нет, сразу завершаем
            return await finish_room(update, context)
        else:
            # Начинаем сбор данных о первой двери
            await update.message.reply_text(
                f'Нужно добавить {count} дверей.\n\n'
                f'Дверь №1:\n'
                f'На какой стене находится вход?',
                reply_markup=get_walls_keyboard()
            )
            return DOOR_DATA
            
    except ValueError:
        await update.message.reply_text('❌ Пожалуйста, введите целое число.')
        return DOOR_COUNT

async def add_room_door_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Собираем данные о каждой двери."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Проверяем, не хочет ли пользователь закончить
    if text == '❌ Закончить добавление дверей':
        return await finish_room(update, context)
    
    temp_room = user_data[user_id]['temp_room']
    current_door = temp_room.get('current_door', 0)
    door_count = temp_room.get('door_count', 0)
    
    # Создаем структуру для текущей двери, если её нет
    if 'current_door_data' not in temp_room:
        temp_room['current_door_data'] = {}
    
    # Определяем, какой параметр двери сейчас запрашиваем
    if 'wall' not in temp_room['current_door_data']:
        # Запрашиваем стену
        if text in ['Левая', 'Правая', 'Верхняя', 'Нижняя']:
            temp_room['current_door_data']['wall'] = text.lower()
            await update.message.reply_text(
                f'Дверь №{current_door + 1} на {text} стене.\n'
                'Введите ширину дверного проёма в метрах (например, 0.9):'
            )
            return DOOR_DATA
        else:
            await update.message.reply_text(
                'Пожалуйста, выберите стену из списка:',
                reply_markup=get_walls_keyboard()
            )
            return DOOR_DATA
    
    elif 'width' not in temp_room['current_door_data']:
        # Запрашиваем ширину
        try:
            width = float(text.replace(',', '.'))
            if width <= 0 or width > 3:
                await update.message.reply_text('Ширина двери должна быть от 0.1 до 3 метров:')
                return DOOR_DATA
            
            temp_room['current_door_data']['width'] = width
            
            # Запрашиваем отступ
            wall = temp_room['current_door_data']['wall']
            wall_length = temp_room.get('left' if wall == 'левая' else 
                                        'right' if wall == 'правая' else 
                                        'width', 0)
            
            await update.message.reply_text(
                f'Ширина двери: {width}м.\n'
                f'На каком расстоянии от верхнего угла находится дверь на {wall} стене?\n'
                f'(введите число от 0 до {wall_length:.1f}м)'
            )
            return DOOR_DATA
            
        except ValueError:
            await update.message.reply_text('❌ Пожалуйста, введите число.')
            return DOOR_DATA
    
    elif 'offset' not in temp_room['current_door_data']:
        # Запрашиваем отступ
        try:
            offset = float(text.replace(',', '.'))
            wall = temp_room['current_door_data']['wall']
            wall_length = temp_room.get('left' if wall == 'левая' else 
                                        'right' if wall == 'правая' else 
                                        'width', 0)
            
            if offset < 0 or offset > wall_length:
                await update.message.reply_text(f'Отступ должен быть от 0 до {wall_length:.1f}м:')
                return DOOR_DATA
            
            temp_room['current_door_data']['offset'] = offset
            
            # Проверяем, есть ли уже комнаты для соединения
            existing_rooms = [r for r in user_data[user_id]['rooms'] if r.get('id') != temp_room['id']]
            
            if existing_rooms:
                # Спрашиваем, с какой комнатой соединить эту дверь
                await update.message.reply_text(
                    f'С какой комнатой соединить эту дверь?',
                    reply_markup=get_rooms_keyboard(existing_rooms, temp_room['id'])
                )
                return CONNECT_ROOM
            else:
                # Если нет других комнат, просто сохраняем дверь
                temp_room['current_door_data']['connects_to'] = None
                return await save_door_and_continue(update, context)
                
        except ValueError:
            await update.message.reply_text('❌ Пожалуйста, введите число.')
            return DOOR_DATA
    
    return DOOR_DATA

async def connect_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора комнаты для соединения."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == '❌ Отмена':
        user_data[user_id]['temp_room']['current_door_data']['connects_to'] = None
        return await save_door_and_continue(update, context)
    
    # Извлекаем ID комнаты из текста
    import re
    match = re.search(r'ID: (\d+)', text)
    if match:
        room_id = int(match.group(1))
        user_data[user_id]['temp_room']['current_door_data']['connects_to'] = room_id
        return await save_door_and_continue(update, context)
    else:
        await update.message.reply_text('Пожалуйста, выберите комнату из списка:')
        return CONNECT_ROOM

async def save_door_and_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем дверь и продолжаем или завершаем."""
    user_id = update.effective_user.id
    temp_room = user_data[user_id]['temp_room']
    
    # Сохраняем дверь
    temp_room['doors'].append(temp_room['current_door_data'].copy())
    temp_room['current_door'] = temp_room.get('current_door', 0) + 1
    
    # Очищаем временные данные текущей двери
    del temp_room['current_door_data']
    
    # Проверяем, все ли двери добавили
    if temp_room['current_door'] >= temp_room.get('door_count', 0):
        return await finish_room(update, context)
    else:
        # Запрашиваем следующую дверь
        await update.message.reply_text(
            f'✅ Дверь №{temp_room["current_door"]} добавлена.\n\n'
            f'Дверь №{temp_room["current_door"] + 1}:\n'
            f'На какой стене находится вход?',
            reply_markup=get_walls_keyboard()
        )
        return DOOR_DATA

async def finish_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершаем добавление комнаты."""
    user_id = update.effective_user.id
    
    # Добавляем комнату в общий список
    new_room = user_data[user_id]['temp_room'].copy()
    
    # Удаляем временные поля
    new_room.pop('door_count', None)
    new_room.pop('current_door', None)
    new_room.pop('current_door_data', None)
    
    # Инициализируем поле для высоты стен
    if 'wall_height' not in new_room:
        new_room['wall_height'] = None
    
    user_data[user_id]['rooms'].append(new_room)
    user_data[user_id]['next_room_id'] += 1
    
    # Очищаем временные данные
    del user_data[user_id]['temp_room']
    
    # Создаем план с новой комнатой
    image_bio = draw_floor_plan(user_data[user_id]['rooms'], new_room)
    
    area = ((new_room['left'] + new_room['right']) / 2) * new_room['width']
    door_count = len(new_room.get('doors', []))
    connections = sum(1 for d in new_room.get('doors', []) if d.get('connects_to') is not None)
    
    # Клавиатура после добавления
    keyboard = [
        ['➕ Добавить ещё комнату'],
        ['📊 Показать общий план'],
        ['🧮 Расчёт материалов'],
        ['🏠 В главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    door_text = f"\n🚪 Дверей: {door_count}"
    if connections > 0:
        door_text += f"\n🔗 Соединений с другими комнатами: {connections}"
    
    await update.message.reply_photo(
        photo=image_bio,
        caption=f"✅ Комната \"{new_room['name']}\" (ID: {new_room['id']}) добавлена!\n"
                f"📏 Левая стена: {new_room['left']}м\n"
                f"📏 Правая стена: {new_room['right']}м\n"
                f"📐 Ширина: {new_room['width']}м\n"
                f"📊 Площадь: {area:.2f} м²"
                f"{door_text}",
        reply_markup=reply_markup
    )
    
    # Завершаем диалог
    return ConversationHandler.END

async def cancel_add_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена добавления комнаты."""
    user_id = update.effective_user.id
    if user_id in user_data and 'temp_room' in user_data[user_id]:
        del user_data[user_id]['temp_room']
    await update.message.reply_text(
        '❌ Добавление комнаты отменено.',
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END

# --- НОВЫЕ ОБРАБОТЧИКИ ДЛЯ РАСЧЁТА МАТЕРИАЛОВ ---
async def start_material_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало расчёта материалов."""
    user_id = update.effective_user.id
    
    if not user_data[user_id]['rooms']:
        await update.message.reply_text(
            '📭 У вас пока нет добавленных комнат. Сначала добавьте хотя бы одну комнату.',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    # Выбираем тип материала
    await update.message.reply_text(
        '🧮 Выберите тип материала для расчёта:',
        reply_markup=get_material_type_keyboard()
    )
    return MATERIAL_TYPE

async def select_material_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор типа материала."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == '❌ Отмена':
        await update.message.reply_text(
            'Расчёт отменён.',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    if 'Обои' in text:
        context.user_data['material_type'] = 'wallpaper'
        await update.message.reply_text(
            'Выберите комнату для расчёта обоев:',
            reply_markup=get_rooms_keyboard(user_data[user_id]['rooms'])
        )
        return SELECT_ROOM_FOR_MATERIAL
    
    elif 'Ламинат' in text:
        context.user_data['material_type'] = 'laminate'
        await update.message.reply_text(
            'Выберите комнату для расчёта ламината:',
            reply_markup=get_rooms_keyboard(user_data[user_id]['rooms'])
        )
        return SELECT_ROOM_FOR_MATERIAL
    
    else:
        await update.message.reply_text(
            'Пожалуйста, выберите тип материала из списка:',
            reply_markup=get_material_type_keyboard()
        )
        return MATERIAL_TYPE

async def select_room_for_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор комнаты для расчёта материалов."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == '❌ Отмена':
        await update.message.reply_text(
            'Расчёт отменён.',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    # Извлекаем ID комнаты
    import re
    match = re.search(r'ID: (\d+)', text)
    if not match:
        await update.message.reply_text(
            'Пожалуйста, выберите комнату из списка:',
            reply_markup=get_rooms_keyboard(user_data[user_id]['rooms'])
        )
        return SELECT_ROOM_FOR_MATERIAL
    
    room_id = int(match.group(1))
    room = next((r for r in user_data[user_id]['rooms'] if r['id'] == room_id), None)
    
    if not room:
        await update.message.reply_text(
            'Комната не найдена. Попробуйте снова:',
            reply_markup=get_rooms_keyboard(user_data[user_id]['rooms'])
        )
        return SELECT_ROOM_FOR_MATERIAL
    
    context.user_data['selected_room_id'] = room_id
    
    material_type = context.user_data.get('material_type')
    
    if material_type == 'wallpaper':
        # Проверяем, есть ли высота стен
        if room.get('wall_height'):
            # Если есть, сразу считаем
            return await calculate_wallpaper_for_room(update, context, room)
        else:
            # Если нет, запрашиваем
            await update.message.reply_text(
                f'Для комнаты "{room["name"]}" не указана высота стен.\n'
                'Введите высоту стен в метрах:'
            )
            return WALL_HEIGHT
    
    elif material_type == 'laminate':
        await update.message.reply_text(
            f'Для комнаты "{room["name"]}" площадью {((room["left"] + room["right"]) / 2) * room["width"]:.2f} м²\n\n'
            'Введите размеры доски ламината через пробел (длина ширина в метрах),\n'
            'например: 1.2 0.2'
        )
        return LAMINATE_SIZE

async def set_wall_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка высоты стен для расчёта обоев."""
    user_id = update.effective_user.id
    
    try:
        height = float(update.message.text.replace(',', '.'))
        if height <= 0 or height > 5:
            await update.message.reply_text('Высота стен должна быть от 0.1 до 5 метров:')
            return WALL_HEIGHT
        
        room_id = context.user_data.get('selected_room_id')
        room = next((r for r in user_data[user_id]['rooms'] if r['id'] == room_id), None)
        
        if room:
            # Сохраняем высоту стен в комнату
            room['wall_height'] = height
            return await calculate_wallpaper_for_room(update, context, room)
        else:
            await update.message.reply_text(
                'Ошибка: комната не найдена.',
                reply_markup=get_main_keyboard()
            )
            return ConversationHandler.END
            
    except ValueError:
        await update.message.reply_text('❌ Пожалуйста, введите число.')
        return WALL_HEIGHT

async def calculate_wallpaper_for_room(update: Update, context: ContextTypes.DEFAULT_TYPE, room: Dict):
    """Расчёт обоев для комнаты."""
    result = calculate_wallpaper(room)
    
    if 'error' in result:
        await update.message.reply_text(
            f'❌ {result["error"]}',
            reply_markup=get_main_keyboard()
        )
    else:
        message = (
            f"🧮 Расчёт обоев для комнаты \"{room['name']}\":\n\n"
            f"📏 Периметр стен: {result['perimeter']} м\n"
            f"📐 Высота стен: {result['height']} м\n"
            f"📊 Площадь оклейки: {result['wall_area']} м²\n\n"
            f"📦 Необходимое количество рулонов:\n"
            f"• Без учёта подгонки: {result['rolls_needed']} шт.\n"
            f"• С запасом 10%: {result['rolls_with_margin']} шт.\n\n"
            f"💡 Совет: Покупайте обои с запасом на подгонку рисунка."
        )
        
        await update.message.reply_text(message, reply_markup=get_main_keyboard())
    
    return ConversationHandler.END

async def set_laminate_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установка размеров ламината и расчёт."""
    user_id = update.effective_user.id
    
    try:
        parts = update.message.text.replace(',', '.').split()
        if len(parts) != 2:
            await update.message.reply_text(
                'Пожалуйста, введите два числа через пробел (длина и ширина в метрах):'
            )
            return LAMINATE_SIZE
        
        length = float(parts[0])
        width = float(parts[1])
        
        if length <= 0 or width <= 0 or length > 2 or width > 0.5:
            await update.message.reply_text(
                'Размеры должны быть положительными и не превышать:\n'
                'длина до 2 метров, ширина до 0.5 метров.'
            )
            return LAMINATE_SIZE
        
        room_id = context.user_data.get('selected_room_id')
        room = next((r for r in user_data[user_id]['rooms'] if r['id'] == room_id), None)
        
        if not room:
            await update.message.reply_text(
                'Ошибка: комната не найдена.',
                reply_markup=get_main_keyboard()
            )
            return ConversationHandler.END
        
        result = calculate_laminate(room, length, width)
        
        message = (
            f"🪵 Расчёт ламината для комнаты \"{room['name']}\":\n\n"
            f"📊 Площадь комнаты: {result['room_area']} м²\n"
            f"📏 Размер доски: {length}м x {width}м = {result['plank_area']} м²\n\n"
            f"📦 Необходимое количество досок:\n"
            f"• Без запаса: {result['planks_needed']} шт.\n"
            f"• С запасом (прямая укладка 7%): {result['planks_with_margin_straight']} шт.\n"
            f"• С запасом (диагональная 10%): {result['planks_with_margin_diagonal']} шт.\n\n"
            f"📦 Примерно упаковок (по 8 шт.): {result['packs_needed']} шт.\n\n"
            f"💡 Совет: Покупайте ламинат с запасом на подрезку."
        )
        
        await update.message.reply_text(message, reply_markup=get_main_keyboard())
        
    except ValueError:
        await update.message.reply_text(
            '❌ Пожалуйста, введите два числа через пробел (например: 1.2 0.2)'
        )
        return LAMINATE_SIZE
    
    return ConversationHandler.END

# --- НОВЫЕ ОБРАБОТЧИКИ ДЛЯ РЕДАКТИРОВАНИЯ ---
async def start_edit_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования комнаты."""
    user_id = update.effective_user.id
    
    if not user_data[user_id]['rooms']:
        await update.message.reply_text(
            '📭 У вас пока нет добавленных комнат.',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        '✏️ Выберите комнату для редактирования:',
        reply_markup=get_rooms_keyboard(user_data[user_id]['rooms'])
    )
    return SELECT_ROOM_FOR_EDIT

async def select_room_for_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор комнаты для редактирования."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == '❌ Отмена':
        await update.message.reply_text(
            'Редактирование отменено.',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    # Извлекаем ID комнаты
    import re
    match = re.search(r'ID: (\d+)', text)
    if not match:
        await update.message.reply_text(
            'Пожалуйста, выберите комнату из списка:',
            reply_markup=get_rooms_keyboard(user_data[user_id]['rooms'])
        )
        return SELECT_ROOM_FOR_EDIT
    
    room_id = int(match.group(1))
    room = next((r for r in user_data[user_id]['rooms'] if r['id'] == room_id), None)
    
    if not room:
        await update.message.reply_text(
            'Комната не найдена. Попробуйте снова:',
            reply_markup=get_rooms_keyboard(user_data[user_id]['rooms'])
        )
        return SELECT_ROOM_FOR_EDIT
    
    context.user_data['edit_room_id'] = room_id
    
    # Показываем текущие параметры
    area = ((room['left'] + room['right']) / 2) * room['width']
    height_text = f"{room.get('wall_height', 'не указана')} м" if room.get('wall_height') else "не указана"
    
    await update.message.reply_text(
        f"✏️ Редактирование комнаты \"{room['name']}\"\n\n"
        f"Текущие параметры:\n"
        f"• Левая стена: {room['left']} м\n"
        f"• Правая стена: {room['right']} м\n"
        f"• Ширина: {room['width']} м\n"
        f"• Площадь: {area:.2f} м²\n"
        f"• Высота стен: {height_text}\n"
        f"• Дверей: {len(room.get('doors', []))}\n\n"
        f"Что хотите изменить?",
        reply_markup=get_edit_options_keyboard()
    )
    return EDIT_OPTION

async def select_edit_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор параметра для редактирования."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == '❌ Отмена':
        await update.message.reply_text(
            'Редактирование отменено.',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    room_id = context.user_data.get('edit_room_id')
    room = next((r for r in user_data[user_id]['rooms'] if r['id'] == room_id), None)
    
    if not room:
        await update.message.reply_text(
            'Ошибка: комната не найдена.',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    if 'Размеры стен' in text:
        context.user_data['edit_field'] = 'walls'
        await update.message.reply_text(
            'Введите новую длину ЛЕВОЙ стены в метрах:'
        )
        return EDIT_VALUE
    
    elif 'Ширину' in text:
        context.user_data['edit_field'] = 'width'
        await update.message.reply_text(
            f'Введите новую ширину комнаты (текущая: {room["width"]} м):'
        )
        return EDIT_VALUE
    
    elif 'Высоту стен' in text:
        context.user_data['edit_field'] = 'height'
        current = room.get('wall_height', 'не указана')
        await update.message.reply_text(
            f'Введите новую высоту стен в метрах (текущая: {current if current != "не указана" else current}):'
        )
        return EDIT_VALUE
    
    elif 'Двери' in text:
        # Здесь можно добавить редактирование дверей
        await update.message.reply_text(
            '🚪 Редактирование дверей будет добавлено в следующей версии.\n\n'
            'Пока вы можете удалить комнату и создать заново с нужными дверями.',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    else:
        await update.message.reply_text(
            'Пожалуйста, выберите опцию из списка:',
            reply_markup=get_edit_options_keyboard()
        )
        return EDIT_OPTION

async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Редактирование значения."""
    user_id = update.effective_user.id
    
    try:
        value = float(update.message.text.replace(',', '.'))
        
        room_id = context.user_data.get('edit_room_id')
        room = next((r for r in user_data[user_id]['rooms'] if r['id'] == room_id), None)
        
        if not room:
            await update.message.reply_text(
                'Ошибка: комната не найдена.',
                reply_markup=get_main_keyboard()
            )
            return ConversationHandler.END
        
        edit_field = context.user_data.get('edit_field')
        
        if edit_field == 'walls':
            # Редактируем левую стену
            if value <= 0 or value > 50:
                await update.message.reply_text('Длина стены должна быть от 0.1 до 50 метров:')
                return EDIT_VALUE
            room['left'] = value
            
            # Запрашиваем правую стену
            await update.message.reply_text(
                f'Левая стена обновлена: {value} м.\n'
                f'Теперь введите новую длину ПРАВОЙ стены (текущая: {room["right"]} м):'
            )
            context.user_data['edit_field'] = 'walls_right'
            return EDIT_VALUE
        
        elif edit_field == 'walls_right':
            if value <= 0 or value > 50:
                await update.message.reply_text('Длина стены должна быть от 0.1 до 50 метров:')
                return EDIT_VALUE
            room['right'] = value
            
            await update.message.reply_text(
                f'✅ Размеры стен обновлены!\n'
                f'Левая: {room["left"]} м, Правая: {room["right"]} м',
                reply_markup=get_main_keyboard()
            )
            
            # Показываем обновлённый план
            image_bio = draw_floor_plan(user_data[user_id]['rooms'])
            await update.message.reply_photo(photo=image_bio, caption="📐 Обновлённый план")
            
            return ConversationHandler.END
        
        elif edit_field == 'width':
            if value <= 0 or value > 50:
                await update.message.reply_text('Ширина должна быть от 0.1 до 50 метров:')
                return EDIT_VALUE
            
            old_width = room['width']
            room['width'] = value
            
            # Обновляем отступы дверей пропорционально, если нужно
            for door in room.get('doors', []):
                if door['wall'] in ['верхняя', 'нижняя']:
                    door['offset'] = door['offset'] * (value / old_width) if old_width > 0 else door['offset']
            
            await update.message.reply_text(
                f'✅ Ширина комнаты обновлена: {value} м (было {old_width} м)',
                reply_markup=get_main_keyboard()
            )
            
            # Показываем обновлённый план
            image_bio = draw_floor_plan(user_data[user_id]['rooms'])
            await update.message.reply_photo(photo=image_bio, caption="📐 Обновлённый план")
            
            return ConversationHandler.END
        
        elif edit_field == 'height':
            if value <= 0 or value > 5:
                await update.message.reply_text('Высота стен должна быть от 0.1 до 5 метров:')
                return EDIT_VALUE
            
            old_height = room.get('wall_height', 'не указана')
            room['wall_height'] = value
            
            await update.message.reply_text(
                f'✅ Высота стен обновлена: {value} м (было {old_height})',
                reply_markup=get_main_keyboard()
            )
            return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text('❌ Пожалуйста, введите число.')
        return EDIT_VALUE

# --- Обработчики обычного меню ---
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки меню (когда не в диалоге)."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in user_data:
        user_data[user_id] = {'rooms': [], 'next_room_id': 0}
    
    if text == '➕ Добавить комнату':
        await add_room_start(update, context)
        return
    
    elif text == '➕ Добавить ещё комнату':
        await add_room_start(update, context)
        return
    
    elif text == '📋 Список комнат':
        if not user_data[user_id]['rooms']:
            await update.message.reply_text(
                '📭 У вас пока нет добавленных комнат.',
                reply_markup=get_main_keyboard()
            )
        else:
            rooms_list = "📋 Список комнат:\n\n"
            total = 0
            total_doors = 0
            total_connections = 0
            for i, room in enumerate(user_data[user_id]['rooms'], 1):
                area = ((room['left'] + room['right']) / 2) * room['width']
                door_count = len(room.get('doors', []))
                connections = sum(1 for d in room.get('doors', []) if d.get('connects_to') is not None)
                total += area
                total_doors += door_count
                total_connections += connections
                height_text = f", h={room['wall_height']}м" if room.get('wall_height') else ""
                rooms_list += f"{i}. {room['name']} (ID: {room['id']}): {area:.1f} м²{height_text}"
                rooms_list += f" (🚪{door_count} дверей"
                if connections > 0:
                    rooms_list += f", 🔗{connections} соединений"
                rooms_list += ")\n"
            rooms_list += f"\n📊 Общая площадь: {total:.1f} м²"
            rooms_list += f"\n🚪 Всего дверей: {total_doors}"
            rooms_list += f"\n🔗 Всего соединений: {total_connections//2}"
            await update.message.reply_text(rooms_list, reply_markup=get_main_keyboard())
    
    elif text in ['📊 Показать общий план', '📊 Общий план']:
        if not user_data[user_id]['rooms']:
            await update.message.reply_text(
                '📭 Нет комнат для отображения. Добавьте хотя бы одну комнату.',
                reply_markup=get_main_keyboard()
            )
        else:
            try:
                image_bio = draw_floor_plan(user_data[user_id]['rooms'])
                
                # Создаём инлайн-клавиатуру
                keyboard = [
                    [InlineKeyboardButton("📝 Детали комнат", callback_data="details")],
                    [InlineKeyboardButton("➕ Добавить комнату", callback_data="add_room")],
                    [InlineKeyboardButton("🧮 Расчёт материалов", callback_data="calculate")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_photo(
                    photo=image_bio,
                    caption="📐 Общий план всех помещений",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Ошибка при создании плана: {e}")
                await update.message.reply_text(
                    "❌ Произошла ошибка при создании плана.",
                    reply_markup=get_main_keyboard()
                )
    
    elif text == '🧮 Расчёт материалов':
        # Запускаем диалог расчёта
        await start_material_calculation(update, context)
    
    elif text == '✏️ Редактировать комнату':
        # Запускаем диалог редактирования
        await start_edit_room(update, context)
    
    elif text == '🔗 Схема соединений':
        if not user_data[user_id]['rooms']:
            await update.message.reply_text(
                '📭 Нет комнат для отображения.',
                reply_markup=get_main_keyboard()
            )
        else:
            # Показываем схему соединений
            connections_text = "🔗 Схема соединений комнат:\n\n"
            for room in user_data[user_id]['rooms']:
                for door in room.get('doors', []):
                    if door.get('connects_to') is not None:
                        connected_room = next(
                            (r for r in user_data[user_id]['rooms'] if r['id'] == door['connects_to']),
                            None
                        )
                        if connected_room:
                            connections_text += f"• {room['name']} (ID:{room['id']}) "
                            connections_text += f"←{door['wall']} стена→ "
                            connections_text += f"{connected_room['name']} (ID:{connected_room['id']})\n"
                            connections_text += f"  🚪 Ширина: {door['width']}м, отступ: {door['offset']}м\n\n"
            
            if connections_text == "🔗 Схема соединений комнат:\n\n":
                connections_text += "Нет соединений между комнатами"
            
            await update.message.reply_text(connections_text, reply_markup=get_main_keyboard())
    
    elif text == '🏠 В главное меню':
        await update.message.reply_text(
            'Главное меню:',
            reply_markup=get_main_keyboard()
        )
    
    elif text == '❌ Очистить всё':
        user_data[user_id]['rooms'] = []
        user_data[user_id]['next_room_id'] = 0
        if 'temp_room' in user_data[user_id]:
            del user_data[user_id]['temp_room']
        await update.message.reply_text(
            '✅ Все данные очищены.',
            reply_markup=get_main_keyboard()
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на инлайн-кнопки."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "details":
        if user_id in user_data and user_data[user_id]['rooms']:
            details = "📝 Детали комнат:\n\n"
            total = 0
            total_doors = 0
            for i, room in enumerate(user_data[user_id]['rooms'], 1):
                area = ((room['left'] + room['right']) / 2) * room['width']
                door_count = len(room.get('doors', []))
                total += area
                total_doors += door_count
                
                details += f"{i}. {room['name']} (ID: {room['id']}):\n"
                details += f"   📏 Левая: {room['left']}м\n"
                details += f"   📏 Правая: {room['right']}м\n"
                details += f"   📐 Ширина: {room['width']}м\n"
                details += f"   📊 Площадь: {area:.2f} м²\n"
                
                if room.get('wall_height'):
                    details += f"   🧱 Высота стен: {room['wall_height']}м\n"
                
                if door_count > 0:
                    details += f"   🚪 Двери:\n"
                    for j, door in enumerate(room['doors'], 1):
                        details += f"      {j}. {door['wall']} стена: "
                        details += f"{door['width']}м x {door['offset']}м от верха"
                        if door.get('connects_to') is not None:
                            connected_room = next(
                                (r for r in user_data[user_id]['rooms'] if r['id'] == door['connects_to']),
                                None
                            )
                            if connected_room:
                                details += f" → соединена с {connected_room['name']}"
                        details += "\n"
                else:
                    details += "   🚪 Дверей нет\n"
                details += "\n"
            
            details += f"📊 Общая площадь: {total:.2f} м²\n"
            details += f"🚪 Всего дверей: {total_doors}"
            
            # Редактируем подпись к фото
            await query.edit_message_caption(caption=details[:1024])
    
    elif query.data == "add_room":
        # Запускаем диалог добавления комнаты
        await query.message.reply_text("Введите название новой комнаты:")
    
    elif query.data == "calculate":
        # Запускаем расчёт материалов
        await query.message.reply_text(
            "🧮 Для расчёта материалов используйте кнопку в главном меню.",
            reply_markup=get_main_keyboard()
        )

# --- Основная функция ---
def main():
    """Запуск бота."""
    # Вставьте сюда свой токен
    TOKEN = "YOUR_BOT_TOKEN"  # ЗАМЕНИТЕ НА СВОЙ ТОКЕН!
    
    if TOKEN == "YOUR_BOT_TOKEN":
        print("❌ ОШИБКА: Замените 'YOUR_BOT_TOKEN' на реальный токен бота!")
        print("Получить токен можно у @BotFather в Telegram")
        return
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Создаем ConversationHandler для добавления комнаты
    add_room_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^➕ Добавить комнату$'), add_room_start),
            MessageHandler(filters.Regex('^➕ Добавить ещё комнату$'), add_room_start),
            CallbackQueryHandler(handle_callback, pattern="^add_room$")
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_room_name)],
            LEFT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_room_left)],
            RIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_room_right)],
            WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_room_width)],
            DOOR_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_room_door_count)],
            DOOR_DATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_room_door_data)],
            CONNECT_ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, connect_room)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_add_room),
            MessageHandler(filters.Regex('^(❌ Отмена|/cancel)$'), cancel_add_room)
        ],
        name="add_room_conversation",
        persistent=False
    )
    
    # Создаем ConversationHandler для расчёта материалов
    material_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🧮 Расчёт материалов$'), start_material_calculation)],
        states={
            MATERIAL_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_material_type)],
            SELECT_ROOM_FOR_MATERIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_room_for_material)],
            WALL_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_wall_height)],
            LAMINATE_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_laminate_size)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_add_room),
            MessageHandler(filters.Regex('^(❌ Отмена|/cancel)$'), cancel_add_room)
        ],
        name="material_conversation",
        persistent=False
    )
    
    # Создаем ConversationHandler для редактирования комнат
    edit_room_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^✏️ Редактировать комнату$'), start_edit_room)],
        states={
            SELECT_ROOM_FOR_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_room_for_edit)],
            EDIT_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_edit_option)],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_add_room),
            MessageHandler(filters.Regex('^(❌ Отмена|/cancel)$'), cancel_add_room)
        ],
        name="edit_room_conversation",
        persistent=False
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler('start', start))
    application.add_handler(add_room_conv)
    application.add_handler(material_conv)
    application.add_handler(edit_room_conv)
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    
    print("🤖 Бот запущен и готов к работе!")
    print("Нажмите Ctrl+C для остановки")
    
    # Запускаем
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)