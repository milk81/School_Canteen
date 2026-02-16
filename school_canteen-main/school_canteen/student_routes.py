from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from functools import wraps
from data_manager import get_user_by_id, get_menu_items, recharge_balance, get_user_payments, load_json, save_json
from data_manager import get_reviews_by_student, get_menu_item_by_id, get_reviews_by_menu_item
from data_manager import create_order, get_user_orders, add_payment, update_user, get_user_nutrition_stats, get_user_active_subscriptions_count
from datetime import datetime

student_bp = Blueprint('student', __name__)


def student_required(f):
    """Декоратор для проверки прав ученика"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'student':
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function


@student_bp.route('/dashboard')
@student_required
def dashboard():
    """Панель управления ученика"""
    user = get_user_by_id(session['user_id'])
    today = datetime.now().strftime('%Y-%m-%d')

    # Получаем сегодняшнее меню
    breakfast_items = get_menu_items(date=today, meal_type='breakfast')
    lunch_items = get_menu_items(date=today, meal_type='lunch')

    # Получаем последние платежи (последние 5)
    payments = sorted(get_user_payments(session['user_id']), key=lambda p: p.get('date', ''), reverse=True)[:5]

    # Получаем сегодняшние заказы
    today_orders = get_user_orders(session['user_id'], today)

    # Получаем отзывы
    reviews = get_reviews_by_student(session['user_id'])

    # Статистика питания для отображения на дашборде
    nutrition = get_user_nutrition_stats(session['user_id'])
    meals_this_month = nutrition.get('meals_this_month', 0)
    active_subscriptions = get_user_active_subscriptions_count(session['user_id'])

    return render_template('student/dashboard.html',
                           user=user,
                           breakfast_items=breakfast_items[:3],
                           lunch_items=lunch_items[:3],
                           payments=payments,
                           today_orders=today_orders,
                           reviews_count=len(reviews),
                           today=today,
                           meals_this_month=meals_this_month,
                           active_subscriptions=active_subscriptions)


@student_bp.route('/menu')
@student_required
def menu():
    """Просмотр меню"""
    meal_type = request.args.get('type', 'all')
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    menu_items = get_menu_items(date=date, meal_type=meal_type)

    # Группируем по типам питания
    breakfast_items = [item for item in menu_items if item['type'] == 'breakfast']
    lunch_items = [item for item in menu_items if item['type'] == 'lunch']

    # Проверяем, какие блюда уже заказаны сегодня
    today_orders = get_user_orders(session['user_id'], date)
    ordered_items = [order['menu_item_id'] for order in today_orders]

    return render_template('student/menu.html',
                           breakfast_items=breakfast_items,
                           lunch_items=lunch_items,
                           meal_type=meal_type,
                           selected_date=date,
                           ordered_items=ordered_items)


@student_bp.route('/profile', methods=['GET', 'POST'])
@student_required
def profile():
    """Профиль ученика"""
    user = get_user_by_id(session['user_id'])

    if request.method == 'POST':
        # Обработка пополнения баланса
        if 'recharge_amount' in request.form:
            try:
                amount = int(request.form.get('recharge_amount', 0))
                if amount <= 0 or amount > 10000:
                    flash('Сумма должна быть от 1 до 10,000 руб.', 'danger')
                else:
                    if recharge_balance(session['user_id'], amount):
                        flash(f'Баланс успешно пополнен на {amount} руб.', 'success')
                        user = get_user_by_id(session['user_id'])  # Обновляем данные пользователя
                    else:
                        flash('Ошибка при пополнении баланса', 'danger')
            except ValueError:
                flash('Неверная сумма', 'danger')

        # Обработка аллергий
        elif 'allergies' in request.form:
            allergies = request.form.get('allergies', '')
            preferences = request.form.getlist('preferences')

            allergies_list = [a.strip() for a in allergies.split(',') if a.strip()]

            update_user(session['user_id'], {
                'allergies': allergies_list,
                'preferences': preferences
            })

            flash('Профиль обновлен', 'success')
            user = get_user_by_id(session['user_id'])

    # Получаем историю платежей (последние 10)
    payments = sorted(get_user_payments(session['user_id']), key=lambda p: p.get('date', ''), reverse=True)

    # Статистика питания для профиля
    nutrition = get_user_nutrition_stats(session['user_id'])

    return render_template('student/profile.html',
                           user=user,
                           payments=payments[:10],
                           nutrition=nutrition)


@student_bp.route('/pay', methods=['POST'])
@student_required
def pay():
    """Оплата питания"""
    try:
        amount = int(request.form.get('amount', 0))
        payment_type = request.form.get('type', 'single')
        description = request.form.get('description', 'Оплата питания')

        if amount <= 0:
            flash('Сумма должна быть положительной', 'danger')
            return redirect(url_for('student.dashboard'))

        user = get_user_by_id(session['user_id'])

        # Проверяем баланс
        if user['balance'] < amount:
            flash('Недостаточно средств на балансе', 'danger')
            return redirect(url_for('student.dashboard'))

        # Обрабатываем платеж
        if payment_type == 'subscription':
            # Для абонемента списываем средства
            new_balance = user['balance'] - amount
            update_user(session['user_id'], {'balance': new_balance})

            # Записываем платеж
            add_payment(session['user_id'], amount, 'subscription', description)

            flash(f'Абонемент оплачен на сумму {amount} руб.', 'success')
        else:
            # Для разового платежа просто списываем
            new_balance = user['balance'] - amount
            update_user(session['user_id'], {'balance': new_balance})

            # Записываем платеж
            add_payment(session['user_id'], amount, 'single', description)

            flash(f'Разовый платеж на сумму {amount} руб. успешно выполнен', 'success')

    except ValueError:
        flash('Неверная сумма', 'danger')

    return redirect(url_for('student.dashboard'))


@student_bp.route('/order/<int:menu_item_id>')
@student_required
def order_meal(menu_item_id):
    """Заказ питания"""
    menu_item = get_menu_item_by_id(menu_item_id)

    if not menu_item:
        flash('Блюдо не найдено', 'danger')
        return redirect(url_for('student.menu'))

    # Проверяем баланс
    user = get_user_by_id(session['user_id'])
    if user['balance'] < menu_item['price']:
        flash('Недостаточно средств для заказа', 'danger')
        return redirect(url_for('student.menu'))

    # Создаем заказ
    if create_order(session['user_id'], menu_item_id):
        flash(f'Вы успешно заказали "{menu_item["name"]}"', 'success')
    else:
        flash('Вы уже заказывали это блюдо сегодня', 'warning')

    return redirect(request.referrer or url_for('student.menu'))


@student_bp.route('/review/<int:menu_item_id>', methods=['GET', 'POST'])
@student_required
def review(menu_item_id):
    """Оставление отзыва о блюде"""
    menu_item = get_menu_item_by_id(menu_item_id)

    if not menu_item:
        flash('Блюдо не найдено', 'danger')
        return redirect(url_for('student.menu'))

    # Проверяем, ел ли ученик это блюдо
    user_orders = get_user_orders(session['user_id'])
    has_ordered = any(order.get('menu_item_id') == menu_item_id for order in user_orders)

    if not has_ordered:
        flash('Вы не можете оставить отзыв о блюде, которое не заказывали', 'warning')
        return redirect(url_for('student.menu'))

    # Проверяем, не оставлял ли уже отзыв
    existing_reviews = get_reviews_by_student(session['user_id'])
    has_reviewed = any(review.get('menu_item_id') == menu_item_id for review in existing_reviews)

    if request.method == 'POST':
        if has_reviewed:
            flash('Вы уже оставляли отзыв об этом блюде', 'warning')
            return redirect(url_for('student.menu'))

        rating = int(request.form.get('rating', 5))
        comment = request.form.get('comment', '').strip()

        if not comment:
            flash('Пожалуйста, напишите комментарий', 'danger')
        elif rating < 1 or rating > 5:
            flash('Оценка должна быть от 1 до 5', 'danger')
        else:
            # Добавляем отзыв
            from data_manager import load_json, save_json
            reviews_data = load_json('data/reviews.json')

            if 'reviews' not in reviews_data:
                reviews_data['reviews'] = []

            new_review = {
                'id': len(reviews_data['reviews']) + 1,
                'student_id': session['user_id'],
                'menu_item_id': menu_item_id,
                'rating': rating,
                'comment': comment,
                'date': datetime.now().isoformat(),
                'approved': True  # Для упрощения сразу одобряем
            }

            reviews_data['reviews'].append(new_review)
            save_json('data/reviews.json', reviews_data)

            flash('Спасибо за ваш отзыв!', 'success')
            return redirect(url_for('student.reviews'))

    # Получаем отзывы других пользователей
    reviews = get_reviews_by_menu_item(menu_item_id)

    return render_template('student/review.html',
                           menu_item=menu_item,
                           has_reviewed=has_reviewed,
                           reviews=reviews)


@student_bp.route('/reviews')
@student_required
def reviews():
    """Просмотр моих отзывов"""
    user_reviews = get_reviews_by_student(session['user_id'])

    # Добавляем информацию о блюдах
    for review in user_reviews:
        menu_item = get_menu_item_by_id(review['menu_item_id'])
        review['menu_item'] = menu_item

    return render_template('student/my_reviews.html', reviews=user_reviews)


@student_bp.route('/orders')
@student_required
def orders():
    """История заказов"""
    user_orders = get_user_orders(session['user_id'])

    # Добавляем информацию о блюдах (если меню_item существует)
    for order in user_orders:
        if 'menu_item_id' in order:
            menu_item = get_menu_item_by_id(order['menu_item_id'])
            order['menu_item'] = menu_item
        else:
            order['menu_item'] = None

    return render_template('student/orders.html', orders=user_orders)

@student_bp.route('/confirm_order/<int:order_id>', methods=['POST'])
@student_required
def confirm_order(order_id):
    """Ученик подтверждает получение своего заказа"""
    orders_data = load_json('data/orders.json')

    for order in orders_data.get('orders', []):
        if order.get('id') == order_id and order.get('student_id') == session['user_id']:
            # Разрешаем подтверждение только если блюдо выдано/подготовлено/отмечено
            if order.get('status') in ('served', 'prepared', 'issued'):
                order['status'] = 'received'
                order['received_at'] = datetime.now().strftime('%H:%M')
                save_json('data/orders.json', orders_data)

                # Синхронизация поля meals_this_month
                try:
                    nutrition = get_user_nutrition_stats(session['user_id'])
                    update_user(session['user_id'], {'meals_this_month': nutrition.get('meals_this_month', 0)})
                except Exception:
                    pass

                flash('Отметка о получении сохранена', 'success')
                return redirect(url_for('student.orders'))
            else:
                flash('Заказ ещё не выдан', 'warning')
                return redirect(url_for('student.orders'))

    flash('Заказ не найден или доступ запрещен', 'danger')
    return redirect(url_for('student.orders'))

@student_bp.route('/payments')
@student_required
def payments():
    """История платежей"""
    user_payments = sorted(get_user_payments(session['user_id']), key=lambda p: p.get('date', ''), reverse=True)
    return render_template('student/payments.html', payments=user_payments)