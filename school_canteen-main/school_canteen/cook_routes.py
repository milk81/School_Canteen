from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from functools import wraps
from data_manager import get_menu_items, load_json, save_json, get_menu_item_by_id, consume_ingredients_for_menu_item
from data_manager import get_user_by_id, update_user
from datetime import datetime

cook_bp = Blueprint('cook', __name__)


def cook_required(f):
    """Декоратор для проверки прав повара"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'cook':
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function


@cook_bp.route('/dashboard')
@cook_required
def dashboard():
    """Панель управления повара"""
    # Получаем инвентарь
    inventory = load_json('data/inventory.json').get('inventory', [])

    # Получаем заявки на закупку
    requests = load_json('data/purchase_requests.json').get('requests', [])

    # Получаем сегодняшние заказы
    orders = load_json('data/orders.json').get('orders', [])
    today = datetime.now().strftime('%Y-%m-%d')
    today_orders = [order for order in orders if order.get('date') == today]

    # Получаем сегодняшнее меню для статистики
    menu_today = get_menu_items(date=today)

    return render_template('cook/dashboard.html',
                           inventory=inventory[:10],
                           requests=requests[:5],
                           today_orders=today_orders,
                           menu_today=menu_today,
                           today=today)


@cook_bp.route('/inventory')
@cook_required
def inventory():
    """Управление инвентарем"""
    inventory_data = load_json('data/inventory.json')

    # Если инвентарь пустой, создаем тестовые данные
    if not inventory_data.get('inventory'):
        inventory_data['inventory'] = [
            {
                'id': 1,
                'name': 'Картофель',
                'category': 'vegetables',
                'quantity': 50,
                'unit': 'кг',
                'minimum': 10,
                'expires': '2024-12-31',
                'description': 'Свежий картофель'
            },
            {
                'id': 2,
                'name': 'Курица',
                'category': 'meat',
                'quantity': 25,
                'unit': 'кг',
                'minimum': 5,
                'expires': '2024-12-20',
                'description': 'Куриное филе'
            },
            {
                'id': 3,
                'name': 'Молоко',
                'category': 'dairy',
                'quantity': 30,
                'unit': 'л',
                'minimum': 10,
                'expires': '2024-12-15',
                'description': 'Пастеризованное молоко'
            },
            {
                'id': 4,
                'name': 'Морковь',
                'category': 'vegetables',
                'quantity': 15,
                'unit': 'кг',
                'minimum': 5,
                'expires': '2024-12-25',
                'description': 'Свежая морковь'
            },
            {
                'id': 5,
                'name': 'Лук',
                'category': 'vegetables',
                'quantity': 8,
                'unit': 'кг',
                'minimum': 3,
                'expires': '2024-12-28',
                'description': 'Репчатый лук'
            }
        ]
        save_json('data/inventory.json', inventory_data)

    return render_template('cook/inventory.html', inventory=inventory_data.get('inventory', []))


@cook_bp.route('/menu')
@cook_required
def menu():
    """Просмотр меню для повара"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    menu_items = get_menu_items(date=date)

    # Группируем по типам питания
    breakfast_items = [item for item in menu_items if item['type'] == 'breakfast']
    lunch_items = [item for item in menu_items if item['type'] == 'lunch']

    # Получаем заказы на сегодня
    orders_data = load_json('data/orders.json')
    today_orders = [order for order in orders_data.get('orders', [])
                    if order.get('date') == date]

    # Считаем статистику по заказам
    order_stats = {}
    for order in today_orders:
        item_id = order.get('menu_item_id')
        if item_id:
            order_stats[item_id] = order_stats.get(item_id, 0) + 1

    # Получаем студентов для отображения имен
    users_data = load_json('data/users.json')
    students = {user['id']: user for user in users_data.get('users', []) if user.get('role') == 'student'}

    return render_template('cook/menu.html',
                           breakfast_items=breakfast_items,
                           lunch_items=lunch_items,
                           selected_date=date,
                           order_stats=order_stats,
                           today_orders=today_orders,
                           students=students)


@cook_bp.route('/issue_meal', methods=['POST'])
@cook_required
def issue_meal():
    """Выдача питания (через форму повара). Можно указать `menu_item_id` чтобы связать выдачу с блюдом."""
    student_id = request.form.get('student_id')
    meal_type = request.form.get('meal_type')
    menu_item_id = request.form.get('menu_item_id')

    # Добавляем запись о выдаче
    orders_data = load_json('data/orders.json')

    new_order = {
        'id': len(orders_data['orders']) + 1,
        'student_id': int(student_id),
        'meal_type': meal_type,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M'),
        'issued_by': session['user_id'],
        'status': 'issued'
    }

    if menu_item_id:
        try:
            menu_item_id = int(menu_item_id)
            menu_item = get_menu_item_by_id(menu_item_id)
            if menu_item:
                new_order['menu_item_id'] = menu_item_id
                new_order['menu_item_name'] = menu_item.get('name')
                new_order['type'] = menu_item.get('type')
                new_order['price'] = menu_item.get('price', 0)
        except ValueError:
            pass

    orders_data['orders'].append(new_order)
    save_json('data/orders.json', orders_data)

    # Синхронизируем поле meals_this_month в профиле ученика
    try:
        month_prefix = datetime.now().strftime('%Y-%m')
        monthly_meals = len([
            o for o in orders_data.get('orders', [])
            if o.get('student_id') == int(student_id) and o.get('date', '').startswith(month_prefix)
        ])
        update_user(int(student_id), {'meals_this_month': monthly_meals})
    except Exception:
        pass

    flash('Питание успешно выдано', 'success')
    return redirect(url_for('cook.dashboard'))


@cook_bp.route('/purchase_request', methods=['POST'])
@cook_required
def purchase_request():
    """Создание заявки на закупку"""
    product = request.form.get('product')
    quantity = request.form.get('quantity')
    reason = request.form.get('reason')

    requests_data = load_json('data/purchase_requests.json')

    new_request = {
        'id': len(requests_data['requests']) + 1,
        'product': product,
        'quantity': quantity,
        'reason': reason,
        'status': 'pending',
        'created_by': session['user_id'],
        'created_at': datetime.now().isoformat()
    }

    requests_data['requests'].append(new_request)
    save_json('data/purchase_requests.json', requests_data)

    flash('Заявка на закупку создана', 'success')
    return redirect(url_for('cook.dashboard'))


@cook_bp.route('/prepare_meal/<int:order_id>')
@cook_required
def prepare_meal(order_id):
    """Отметка о приготовлении блюда"""
    orders_data = load_json('data/orders.json')

    for order in orders_data.get('orders', []):
        if order.get('id') == order_id:
            order['status'] = 'prepared'
            order['prepared_by'] = session['user_id']
            order['prepared_at'] = datetime.now().strftime('%H:%M')
            break

    save_json('data/orders.json', orders_data)
    flash('Блюдо отмечено как приготовленное', 'success')
    return redirect(request.referrer or url_for('cook.menu'))


@cook_bp.route('/serve_meal/<int:order_id>')
@cook_required
def serve_meal(order_id):
    """Отметка о выдаче блюда — при выдаче списываем ингредиенты из инвентаря, если блюдо связано с menu_item."""
    orders_data = load_json('data/orders.json')

    served_changes = []
    for order in orders_data.get('orders', []):
        if order.get('id') == order_id:
            order['status'] = 'served'
            order['served_by'] = session['user_id']
            order['served_at'] = datetime.now().strftime('%H:%M')

            # Если заказ связан с блюдом — списываем ингредиенты
            menu_item_id = order.get('menu_item_id')
            if menu_item_id:
                try:
                    changes = consume_ingredients_for_menu_item(menu_item_id, servings=1)
                    served_changes = changes
                except Exception:
                    served_changes = []
            break

    save_json('data/orders.json', orders_data)

    # Показываем результат списания в сообщениях
    if served_changes:
        msgs = []
        low_alerts = []
        for c in served_changes:
            if not c.get('found'):
                msgs.append(f"Не найден ингредиент: {c.get('ingredient')}")
            else:
                msgs.append(f"{c.get('name')}: -{c.get('consumed')} {c.get('unit')} (осталось {c.get('after')} {c.get('unit')})")
                if c.get('low_stock'):
                    low_alerts.append(f"{c.get('name')} (осталось {c.get('after')} {c.get('unit')})")

        flash('<br>'.join(msgs), 'info')
        if low_alerts:
            flash('Низкий остаток: ' + ', '.join(low_alerts), 'warning')

    flash('Блюдо отмечено как выданное', 'success')
    return redirect(request.referrer or url_for('cook.menu'))


@cook_bp.route('/add_inventory', methods=['POST'])
@cook_required
def add_inventory():
    """Добавление продукта в инвентарь"""
    name = request.form.get('name')
    category = request.form.get('category')
    quantity = float(request.form.get('quantity', 0))
    unit = request.form.get('unit')
    minimum = int(request.form.get('minimum', 10))
    expires = request.form.get('expires')
    description = request.form.get('description', '')

    inventory_data = load_json('data/inventory.json')

    if 'inventory' not in inventory_data:
        inventory_data['inventory'] = []

    new_item = {
        'id': len(inventory_data['inventory']) + 1,
        'name': name,
        'category': category,
        'quantity': quantity,
        'unit': unit,
        'minimum': minimum,
        'expires': expires,
        'description': description
    }

    inventory_data['inventory'].append(new_item)
    save_json('data/inventory.json', inventory_data)

    flash(f'Продукт "{name}" добавлен в инвентарь', 'success')
    return redirect(url_for('cook.inventory'))


@cook_bp.route('/consume_ingredients', methods=['POST'])
@cook_required
def consume_ingredients():
    """Ручное списание ингредиентов для блюда (удобство повару)"""
    menu_item_id = request.form.get('menu_item_id')
    servings = int(request.form.get('servings', 1))

    try:
        menu_item_id = int(menu_item_id)
    except Exception:
        flash('Неверный ID блюда', 'danger')
        return redirect(request.referrer or url_for('cook.menu'))

    try:
        changes = consume_ingredients_for_menu_item(menu_item_id, servings=servings)
    except Exception:
        flash('Ошибка при списании ингредиентов', 'danger')
        return redirect(request.referrer or url_for('cook.menu'))

    msgs = []
    low_alerts = []
    for c in changes:
        if not c.get('found'):
            msgs.append(f"Не найден ингредиент: {c.get('ingredient')}")
        else:
            msgs.append(f"{c.get('name')}: -{c.get('consumed')} {c.get('unit')} (осталось {c.get('after')} {c.get('unit')})")
            if c.get('low_stock'):
                low_alerts.append(f"{c.get('name')} (осталось {c.get('after')} {c.get('unit')})")

    flash('<br>'.join(msgs), 'info')
    if low_alerts:
        flash('Низкий остаток: ' + ', '.join(low_alerts), 'warning')

    return redirect(request.referrer or url_for('cook.menu'))


@cook_bp.route('/update_inventory', methods=['POST'])
@cook_required
def update_inventory():
    """Обновление продукта в инвентаре"""
    item_id = int(request.form.get('item_id'))
    quantity = float(request.form.get('quantity', 0))
    expires = request.form.get('expires')
    comment = request.form.get('comment', '')

    inventory_data = load_json('data/inventory.json')

    if 'inventory' not in inventory_data:
        flash('Инвентарь пуст', 'danger')
        return redirect(url_for('cook.inventory'))

    for i, item in enumerate(inventory_data['inventory']):
        if item.get('id') == item_id:
            inventory_data['inventory'][i]['quantity'] = quantity
            if expires:
                inventory_data['inventory'][i]['expires'] = expires
            if comment:
                inventory_data['inventory'][i]['comment'] = comment
            break

    save_json('data/inventory.json', inventory_data)
    flash('Инвентарь обновлен', 'success')
    return redirect(url_for('cook.inventory'))


@cook_bp.route('/orders_today')
@cook_required
def orders_today():
    """Просмотр заказов на сегодня"""
    today = datetime.now().strftime('%Y-%m-%d')

    orders_data = load_json('data/orders.json')
    today_orders = [order for order in orders_data.get('orders', [])
                    if order.get('date') == today]

    # Группируем по статусам
    orders_by_status = {
        'ordered': [],
        'prepared': [],
        'served': []
    }

    for order in today_orders:
        status = order.get('status', 'ordered')
        if status in orders_by_status:
            orders_by_status[status].append(order)

    # Добавляем информацию о студентах и блюдах
    users_data = load_json('data/users.json')
    students = {user['id']: user for user in users_data.get('users', []) if user.get('role') == 'student'}

    for order in today_orders:
        order['student'] = students.get(order.get('student_id'), {})
        menu_item = get_menu_item_by_id(order.get('menu_item_id'))
        order['menu_item'] = menu_item

    return render_template('cook/orders_today.html',
                           orders_by_status=orders_by_status,
                           today_orders=today_orders,
                           today=today)


@cook_bp.route('/statistics')
@cook_required
def statistics():
    """Статистика для повара"""
    today = datetime.now().strftime('%Y-%m-%d')

    # Получаем заказы за последние 7 дней
    orders_data = load_json('data/orders.json')
    all_orders = orders_data.get('orders', [])

    # Статистика по дням
    stats_by_day = {}
    for order in all_orders:
        date = order.get('date')
        if date:
            if date not in stats_by_day:
                stats_by_day[date] = {'breakfast': 0, 'lunch': 0, 'total': 0}

            if order.get('type') == 'breakfast':
                stats_by_day[date]['breakfast'] += 1
            elif order.get('type') == 'lunch':
                stats_by_day[date]['lunch'] += 1
            stats_by_day[date]['total'] += 1

    # Сортируем по дате
    stats_by_day = dict(sorted(stats_by_day.items(), key=lambda x: x[0], reverse=True)[:7])

    # Статистика по блюдам
    menu_items = {}
    for order in all_orders:
        menu_item_id = order.get('menu_item_id')
        if menu_item_id:
            menu_items[menu_item_id] = menu_items.get(menu_item_id, 0) + 1

    # Получаем названия блюд
    popular_dishes = []
    for item_id, count in sorted(menu_items.items(), key=lambda x: x[1], reverse=True)[:5]:
        menu_item = get_menu_item_by_id(item_id)
        if menu_item:
            popular_dishes.append({
                'name': menu_item.get('name'),
                'count': count
            })

    # Статистика инвентаря
    inventory_data = load_json('data/inventory.json')
    low_stock = [item for item in inventory_data.get('inventory', [])
                 if item.get('quantity', 0) < item.get('minimum', 10)]

    return render_template('cook/statistics.html',
                           stats_by_day=stats_by_day,
                           popular_dishes=popular_dishes,
                           low_stock=low_stock,
                           total_orders=len(all_orders))