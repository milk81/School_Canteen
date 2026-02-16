import json
import os
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from config import *


def init_data_dir():
    """Создаем директорию для данных если её нет"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Инициализируем файлы если их нет или они пустые
    default_data = {
        USERS_FILE: {"users": []},
        MENU_FILE: {"menu": []},
        ORDERS_FILE: {"orders": []},
        INVENTORY_FILE: {"inventory": []},
        PURCHASE_REQUESTS_FILE: {"requests": []},
        REVIEWS_FILE: {"reviews": []},
        'data/payments.json': {"payments": []}
    }

    for file_path, data in default_data.items():
        # Если файл не существует или пустой, создаем с дефолтными данными
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            save_json(file_path, data)

    return True


def create_data_file(file_path, default_data):
    """Создает файл с данными по умолчанию"""
    if not os.path.exists(file_path):
        save_json(file_path, default_data)


def load_json(file_path: str) -> Dict:
    """Загружает данные из JSON файла"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(file_path: str, data: Dict) -> None:
    """Сохраняет данные в JSON файл"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def hash_password(password: str) -> str:
    """Хеширует пароль"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Проверяет пароль"""
    return hash_password(password) == hashed


def add_user(username: str, password: str, role: str, full_name: str, email: str) -> bool:
    """Добавляет нового пользователя"""
    users_data = load_json(USERS_FILE)

    # Инициализируем структуру если её нет
    if 'users' not in users_data:
        users_data = {'users': []}

    # Проверяем, не существует ли пользователь
    if any(user.get('username') == username for user in users_data['users']):
        return False

    # Создаем нового пользователя
    new_user = {
        'id': len(users_data['users']) + 1,
        'username': username,
        'password': hash_password(password),
        'role': role,
        'full_name': full_name,
        'email': email,
        'class': '10А' if role == 'student' else None,
        'allergies': [],
        'preferences': [],
        'balance': 1500 if role == 'student' else 0,
        'created_at': datetime.now().isoformat()
    }

    users_data['users'].append(new_user)
    save_json(USERS_FILE, users_data)
    return True


def get_user_by_username(username: str) -> Optional[Dict]:
    """Находит пользователя по имени"""
    users_data = load_json(USERS_FILE)

    # Проверяем структуру
    if 'users' not in users_data:
        return None

    for user in users_data['users']:
        if user.get('username') == username:
            return user
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Находит пользователя по ID"""
    users_data = load_json(USERS_FILE)

    # Проверяем структуру
    if 'users' not in users_data:
        return None

    for user in users_data['users']:
        if user.get('id') == user_id:
            return user
    return None


def update_user(user_id: int, updates: Dict) -> bool:
    """Обновляет данные пользователя"""
    users_data = load_json(USERS_FILE)

    # Проверяем структуру
    if 'users' not in users_data:
        return False

    for i, user in enumerate(users_data['users']):
        if user.get('id') == user_id:
            users_data['users'][i].update(updates)
            save_json(USERS_FILE, users_data)
            return True
    return False


# Функции для работы с меню
def get_menu_items(date: str = None, meal_type: str = None) -> List[Dict]:
    """Получение меню с фильтрацией"""
    menu_data = load_json(MENU_FILE)

    # Проверяем структуру
    if 'menu' not in menu_data:
        return []

    items = menu_data.get('menu', [])

    if date:
        items = [item for item in items if item.get('date') == date]

    if meal_type and meal_type != 'all':
        items = [item for item in items if item.get('type') == meal_type]

    return items


def get_menu_item_by_id(item_id):
    """Получение блюда по ID"""
    menu_data = load_json(MENU_FILE)

    if 'menu' not in menu_data:
        return None

    for item in menu_data['menu']:
        if item.get('id') == item_id:
            return item

    return None


def add_menu_item(item_data):
    """Добавление нового блюда в меню"""
    menu_data = load_json(MENU_FILE)

    if 'menu' not in menu_data:
        menu_data['menu'] = []

    item_id = len(menu_data['menu']) + 1
    item_data['id'] = item_id
    menu_data['menu'].append(item_data)

    save_json(MENU_FILE, menu_data)
    return item_id


# Функции для отзывов
def get_reviews_by_student(student_id):
    """Получение отзывов ученика"""
    reviews_data = load_json(REVIEWS_FILE)

    if 'reviews' not in reviews_data:
        return []

    return [review for review in reviews_data['reviews']
            if review.get('student_id') == student_id]


def get_reviews_by_menu_item(menu_item_id):
    """Получение отзывов для блюда"""
    reviews_data = load_json(REVIEWS_FILE)

    if 'reviews' not in reviews_data:
        return []

    return [review for review in reviews_data['reviews']
            if review.get('menu_item_id') == menu_item_id and review.get('approved')]


# Функция для добавления платежа
def add_payment(user_id, amount, payment_type, description):
    """Добавляет запись о платеже"""
    payments_data = load_json('data/payments.json')

    if 'payments' not in payments_data:
        payments_data['payments'] = []

    payment = {
        'id': len(payments_data['payments']) + 1,
        'user_id': user_id,
        'amount': amount,
        'type': payment_type,
        'description': description,
        'date': datetime.now().isoformat(),
        'status': 'completed'
    }

    payments_data['payments'].append(payment)
    save_json('data/payments.json', payments_data)
    return payment['id']


# Функция для получения платежей пользователя
def get_user_payments(user_id):
    """Получает платежи пользователя"""
    payments_data = load_json('data/payments.json')

    if 'payments' not in payments_data:
        return []

    return [p for p in payments_data['payments'] if p.get('user_id') == user_id]


def get_user_nutrition_stats(user_id, reference_date=None):
    """Возвращает статистику питания пользователя за текущий месяц:
    - количество питаний (orders)
    - потрачено за месяц (payments, исключая пополнения)
    - средняя стоимость питания (по заказам)
    - время последнего питания (читаем из orders)
    """
    if reference_date is None:
        reference_date = datetime.now()

    month_prefix = f"{reference_date.year}-{reference_date.month:02d}"

    # Заказы пользователя за текущий месяц
    orders_data = load_json(ORDERS_FILE)
    user_orders = [o for o in orders_data.get('orders', [])
                   if o.get('student_id') == user_id and o.get('date', '').startswith(month_prefix)]

    meals_count = len(user_orders)

    # Потрачено: суммарно по платежам пользователя за месяц, исключая 'recharge'
    payments_data = load_json('data/payments.json')
    user_payments_month = [p for p in payments_data.get('payments', [])
                           if p.get('user_id') == user_id and p.get('date', '').startswith(month_prefix)]

    spent_sum = sum(p.get('amount', 0) for p in user_payments_month if p.get('type') != 'recharge')

    # Средняя стоимость по заказам (по заказам из orders)
    avg_cost = 0
    if meals_count > 0:
        avg_cost = round(sum(o.get('price', 0) for o in user_orders) / meals_count)

    # Последнее питание
    all_user_orders = [o for o in load_json(ORDERS_FILE).get('orders', []) if o.get('student_id') == user_id]
    last_meal_display = 'Нет данных'
    if all_user_orders:
        # Составляем datetime для сортировки
        def _order_dt(o):
            try:
                return datetime.strptime(f"{o.get('date')} {o.get('time')}", "%Y-%m-%d %H:%M")
            except Exception:
                return datetime.min

        last_order = max(all_user_orders, key=_order_dt)
        last_dt = _order_dt(last_order)
        if last_dt.date() == reference_date.date():
            last_meal_display = f"Сегодня, {last_dt.strftime('%H:%M')}"
        else:
            last_meal_display = f"{last_order.get('date')}, {last_order.get('time')}"

    return {
        'meals_this_month': meals_count,
        'spent_this_month': spent_sum,
        'avg_cost': avg_cost,
        'last_meal_display': last_meal_display
    }


def get_user_active_subscriptions_count(user_id, days: int = 30):
    """Считает количество оплаченных абонементов пользователя за последние `days` дней."""
    payments_data = load_json('data/payments.json')
    now = datetime.now()
    count = 0
    for p in payments_data.get('payments', []):
        if p.get('user_id') != user_id or p.get('type') != 'subscription':
            continue
        try:
            pd = datetime.fromisoformat(p.get('date'))
        except Exception:
            continue
        if (now - pd).days < days:
            count += 1
    return count


# Функция для пополнения баланса
def recharge_balance(user_id, amount):
    """Пополняет баланс пользователя"""
    user = get_user_by_id(user_id)
    if not user:
        return False

    new_balance = user.get('balance', 0) + amount
    update_user(user_id, {'balance': new_balance})

    # Записываем платеж
    add_payment(user_id, amount, 'recharge', 'Пополнение баланса')

    return True


# Функция для получения заказов пользователя
def get_user_orders(user_id, date=None):
    """Получает заказы пользователя"""
    orders_data = load_json('data/orders.json')

    if 'orders' not in orders_data:
        return []

    orders = [order for order in orders_data['orders'] if order.get('student_id') == user_id]

    if date:
        orders = [order for order in orders if order.get('date') == date]

    return orders


def _find_inventory_item_by_name(name: str):
    """Находит элемент инвентаря по имени (поиск по подстроке, нечувствительно к регистру).
    Возвращает индекс и сам элемент или (None, None) если не найдено."""
    inventory_data = load_json(INVENTORY_FILE)
    for i, item in enumerate(inventory_data.get('inventory', [])):
        if name.lower() in item.get('name', '').lower() or item.get('name', '').lower() in name.lower():
            return i, item
    return None, None


def consume_ingredients_for_menu_item(menu_item_id: int, servings: int = 1):
    """Списывает ингредиенты из инвентаря для указанного блюда.
    - Ищет ингредиенты по полю `contains` у блюда
    - Списывает `servings` единиц (снижение по умолчанию зависит от единицы измерения)
    - Возвращает список изменений для логирования
    """
    menu_item = get_menu_item_by_id(menu_item_id)
    if not menu_item or not menu_item.get('contains'):
        return []

    inventory_data = load_json(INVENTORY_FILE)
    if 'inventory' not in inventory_data:
        inventory_data['inventory'] = []

    changes = []
    for ing in menu_item.get('contains', []):
        idx, inv_item = _find_inventory_item_by_name(ing)
        if idx is None:
            # ингредиент не найден в инвентаре — пропускаем
            changes.append({'ingredient': ing, 'found': False})
            continue

        # Определяем количество списания по единице измерения
        unit = inv_item.get('unit', '')
        if 'кг' in unit or 'л' in unit:
            consume_amount = 0.1 * servings
        elif 'г' in unit or 'мл' in unit:
            consume_amount = 100 * servings
        else:
            # единицы (шт, уп и т.п.)
            consume_amount = 1 * servings

        before = inv_item.get('quantity', 0)
        after = max(0, round(before - consume_amount, 2))
        inventory_data['inventory'][idx]['quantity'] = after

        low = after < inventory_data['inventory'][idx].get('minimum', 10)
        changes.append({
            'ingredient': ing,
            'found': True,
            'item_id': inv_item.get('id'),
            'name': inv_item.get('name'),
            'unit': unit,
            'before': before,
            'after': after,
            'consumed': round(before - after, 2),
            'low_stock': low
        })

    save_json(INVENTORY_FILE, inventory_data)
    return changes

# Функция для создания заказа
def create_order(student_id, menu_item_id):
    """Создает новый заказ"""
    menu_item = get_menu_item_by_id(menu_item_id)
    if not menu_item:
        return False

    orders_data = load_json('data/orders.json')

    if 'orders' not in orders_data:
        orders_data['orders'] = []

    # Проверяем, не заказывал ли уже сегодня это блюдо
    today = datetime.now().strftime('%Y-%m-%d')
    existing_order = any(
        order.get('student_id') == student_id and
        order.get('menu_item_id') == menu_item_id and
        order.get('date') == today
        for order in orders_data['orders']
    )

    if existing_order:
        return False

    new_order = {
        'id': len(orders_data['orders']) + 1,
        'student_id': student_id,
        'menu_item_id': menu_item_id,
        'menu_item_name': menu_item['name'],
        'date': today,
        'time': datetime.now().strftime('%H:%M'),
        'type': menu_item['type'],
        'price': menu_item['price'],
        'status': 'ordered'
    }

    orders_data['orders'].append(new_order)
    save_json('data/orders.json', orders_data)

    # Списываем средства
    user = get_user_by_id(student_id)
    if user:
        new_balance = user['balance'] - menu_item['price']
        update_user(student_id, {'balance': new_balance})

        # Записываем платеж
        add_payment(student_id, menu_item['price'], 'meal_purchase',
                    f"Покупка: {menu_item['name']}")

    # Обновляем количество питаний в профиле пользователя (за текущий месяц)
    try:
        month_prefix = datetime.now().strftime('%Y-%m')
        monthly_meals = len([
            o for o in orders_data.get('orders', [])
            if o.get('student_id') == student_id and o.get('date', '').startswith(month_prefix)
        ])
        # Сохраняем поле meals_this_month в users.json
        update_user(student_id, {'meals_this_month': monthly_meals})
    except Exception:
        # Не критично — не прерываем выполнение при ошибке обновления счётчика
        pass

    return True


def init_all_data():
    """Инициализация всех данных системы"""
    init_data_dir()

    # Создаем все необходимые файлы
    create_data_file(USERS_FILE, {"users": []})
    create_data_file(MENU_FILE, {"menu": []})
    create_data_file(ORDERS_FILE, {"orders": []})
    create_data_file(INVENTORY_FILE, {"inventory": []})
    create_data_file(PURCHASE_REQUESTS_FILE, {"requests": []})
    create_data_file(REVIEWS_FILE, {"reviews": []})
    create_data_file('data/payments.json', {"payments": []})

    # Создаем тестовых пользователей
    users_data = load_json(USERS_FILE)
    existing_usernames = [user.get('username') for user in users_data.get('users', [])]

    test_users = [
        {
            'username': 'admin',
            'password': 'admin123',
            'role': 'admin',
            'full_name': 'Администратор Системы',
            'email': 'admin@school.ru',
            'class': None,
            'allergies': [],
            'balance': 0,
            'created_at': datetime.now().isoformat()
        },
        {
            'username': 'ivanov',
            'password': 'ivanov123',
            'role': 'student',
            'full_name': 'Иванов Иван Иванович',
            'email': 'ivanov@school.ru',
            'class': '10А',
            'allergies': ['орехи', 'молоко'],
            'balance': 1500,
            'meals_this_month': 0,
            'created_at': datetime.now().isoformat()
        },
        {
            'username': 'petrov',
            'password': 'petrov123',
            'role': 'cook',
            'full_name': 'Петров Петр Петрович',
            'email': 'petrov@school.ru',
            'class': None,
            'allergies': [],
            'balance': 0,
            'meals_this_month': 0,
            'created_at': datetime.now().isoformat()
        }
    ]

    for test_user in test_users:
        if test_user['username'] not in existing_usernames:
            # Создаем пользователя
            new_user = {
                'id': len(users_data.get('users', [])) + 1,
                'username': test_user['username'],
                'password': hash_password(test_user['password']),
                'role': test_user['role'],
                'full_name': test_user['full_name'],
                'email': test_user['email'],
                'class': test_user['class'],
                'allergies': test_user['allergies'],
                'balance': test_user['balance'],
                'created_at': test_user['created_at']
            }

            if 'users' not in users_data:
                users_data['users'] = []

            users_data['users'].append(new_user)

    save_json(USERS_FILE, users_data)

    # Создаем тестовое меню
    menu_data = load_json(MENU_FILE)
    if not menu_data.get('menu'):
        today = datetime.now()
        menu_items = []

        for i in range(7):
            date = (today + timedelta(days=i)).strftime('%Y-%m-%d')

            # Завтраки
            menu_items.extend([
                {
                    'id': len(menu_items) + 1,
                    'date': date,
                    'type': 'breakfast',
                    'name': 'Каша манная с маслом',
                    'description': 'Полезная молочная каша',
                    'price': 70,
                    'calories': 250,
                    'allergens': ['молоко', 'глютен'],
                    'contains': ['манка', 'молоко', 'сахар', 'масло'],
                    'available': True
                },
                {
                    'id': len(menu_items) + 1,
                    'date': date,
                    'type': 'breakfast',
                    'name': 'Омлет с сыром',
                    'description': 'Воздушный омлет с сыром',
                    'price': 85,
                    'calories': 220,
                    'allergens': ['яйца', 'молоко'],
                    'contains': ['яйца', 'молоко', 'сыр'],
                    'available': True
                },
                {
                    'id': len(menu_items) + 1,
                    'date': date,
                    'type': 'breakfast',
                    'name': 'Бутерброд с сыром',
                    'description': 'Свежий бутерброд',
                    'price': 60,
                    'calories': 180,
                    'allergens': ['глютен'],
                    'contains': ['хлеб', 'сыр'],
                    'available': True
                }
            ])

            # Обеды
            menu_items.extend([
                {
                    'id': len(menu_items) + 1,
                    'date': date,
                    'type': 'lunch',
                    'name': 'Суп куриный с лапшой',
                    'description': 'Наваристый куриный суп',
                    'price': 120,
                    'calories': 300,
                    'allergens': ['глютен'],
                    'contains': ['курица', 'лапша', 'овощи'],
                    'available': True
                },
                {
                    'id': len(menu_items) + 1,
                    'date': date,
                    'type': 'lunch',
                    'name': 'Котлета с картофельным пюре',
                    'description': 'Домашняя котлета с пюре',
                    'price': 130,
                    'calories': 350,
                    'allergens': ['глютен'],
                    'contains': ['мясо', 'картофель', 'лук'],
                    'available': True
                },
                {
                    'id': len(menu_items) + 1,
                    'date': date,
                    'type': 'lunch',
                    'name': 'Салат овощной',
                    'description': 'Свежий овощной салат',
                    'price': 80,
                    'calories': 150,
                    'allergens': [],
                    'contains': ['помидоры', 'огурцы', 'лук'],
                    'available': True
                }
            ])

        menu_data['menu'] = menu_items
        save_json(MENU_FILE, menu_data)

    return True


# Инициализируем все данные при импорте
init_all_data()