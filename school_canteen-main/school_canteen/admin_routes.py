from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from functools import wraps
from data_manager import load_json, save_json, get_menu_item_by_id, get_user_by_id, get_menu_items
from datetime import datetime

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Декоратор для проверки прав администратора"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Панель управления администратора"""
    # Статистика оплат
    users = load_json('data/users.json').get('users', [])
    students = [user for user in users if user['role'] == 'student']
    total_balance = sum(student.get('balance', 0) for student in students)

    # Заявки на закупку
    requests = load_json('data/purchase_requests.json').get('requests', [])
    pending_requests = [r for r in requests if r['status'] == 'pending']

    # Посещаемость
    orders = load_json('data/orders.json').get('orders', [])
    today = datetime.now().strftime('%Y-%m-%d')
    today_attendance = len([o for o in orders if o.get('date') == today])

    # Отзывы
    reviews = load_json('data/reviews.json').get('reviews', [])
    pending_reviews = [r for r in reviews if not r.get('approved')]

    return render_template('admin/dashboard.html',
                           total_students=len(students),
                           total_balance=total_balance,
                           pending_requests=len(pending_requests),
                           today_attendance=today_attendance,
                           pending_reviews=len(pending_reviews))


@admin_bp.route('/requests')
@admin_required
def requests():
    """Управление заявками на закупку"""
    requests_data = load_json('data/purchase_requests.json')

    # Добавляем информацию о создателе
    users = load_json('data/users.json').get('users', [])
    user_dict = {user['id']: user for user in users}

    for request in requests_data.get('requests', []):
        creator_id = request.get('created_by')
        if creator_id in user_dict:
            request['creator'] = user_dict[creator_id]

    return render_template('admin/requests.html', requests=requests_data.get('requests', []))


@admin_bp.route('/approve_request/<int:request_id>')
@admin_required
def approve_request(request_id):
    """Согласование заявки"""
    requests_data = load_json('data/purchase_requests.json')

    for req in requests_data['requests']:
        if req['id'] == request_id:
            req['status'] = 'approved'
            req['approved_by'] = session['user_id']
            req['approved_at'] = datetime.now().isoformat()
            break

    save_json('data/purchase_requests.json', requests_data)
    flash('Заявка согласована', 'success')
    return redirect(url_for('admin.requests'))


@admin_bp.route('/reject_request/<int:request_id>')
@admin_required
def reject_request(request_id):
    """Отклонение заявки"""
    requests_data = load_json('data/purchase_requests.json')

    for req in requests_data['requests']:
        if req['id'] == request_id:
            req['status'] = 'rejected'
            req['rejected_by'] = session['user_id']
            req['rejected_at'] = datetime.now().isoformat()
            break

    save_json('data/purchase_requests.json', requests_data)
    flash('Заявка отклонена', 'success')
    return redirect(url_for('admin.requests'))


@admin_bp.route('/reports')
@admin_required
def reports():
    """Генерация отчетов"""
    # Получаем данные для отчета
    orders = load_json('data/orders.json').get('orders', [])
    users = load_json('data/users.json').get('users', [])

    # Статистика по дням
    attendance_by_day = {}
    for order in orders:
        date = order.get('date')
        attendance_by_day[date] = attendance_by_day.get(date, 0) + 1

    # Статистика по классам
    class_attendance = {}
    students = {user['id']: user for user in users if user['role'] == 'student'}

    for order in orders:
        student = students.get(order.get('student_id'))
        if student and student.get('class'):
            class_name = student['class']
            class_attendance[class_name] = class_attendance.get(class_name, 0) + 1

    # Финансовая статистика
    payments = load_json('data/payments.json').get('payments', [])
    today = datetime.now().strftime('%Y-%m-%d')
    today_payments = [p for p in payments if p.get('date', '').startswith(today)]
    today_revenue = sum(p.get('amount', 0) for p in today_payments if p.get('type') != 'recharge')

    return render_template('admin/reports.html',
                           attendance_by_day=sorted(attendance_by_day.items()),
                           class_attendance=sorted(class_attendance.items()),
                           total_orders=len(orders),
                           today_revenue=today_revenue)


@admin_bp.route('/reviews')
@admin_required
def reviews():
    """Управление отзывами"""
    reviews_data = load_json('data/reviews.json')

    if 'reviews' not in reviews_data:
        reviews_data['reviews'] = []

    # Добавляем информацию о блюдах и пользователях
    for review in reviews_data['reviews']:
        menu_item = get_menu_item_by_id(review.get('menu_item_id'))
        student = get_user_by_id(review.get('student_id'))

        review['menu_item'] = menu_item
        review['student'] = student

    return render_template('admin/reviews.html', reviews=reviews_data['reviews'])


@admin_bp.route('/approve_review/<int:review_id>')
@admin_required
def approve_review(review_id):
    """Одобрение отзыва"""
    reviews_data = load_json('data/reviews.json')

    if 'reviews' not in reviews_data:
        flash('Отзывы не найдены', 'danger')
        return redirect(url_for('admin.reviews'))

    for i, review in enumerate(reviews_data['reviews']):
        if review.get('id') == review_id:
            reviews_data['reviews'][i]['approved'] = True
            reviews_data['reviews'][i]['approved_at'] = datetime.now().isoformat()
            save_json('data/reviews.json', reviews_data)
            flash('Отзыв одобрен', 'success')
            return redirect(url_for('admin.reviews'))

    flash('Отзыв не найден', 'danger')
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/reject_review/<int:review_id>')
@admin_required
def reject_review(review_id):
    """Отклонение отзыва"""
    reviews_data = load_json('data/reviews.json')

    if 'reviews' not in reviews_data:
        flash('Отзывы не найдены', 'danger')
        return redirect(url_for('admin.reviews'))

    for i, review in enumerate(reviews_data['reviews']):
        if review.get('id') == review_id:
            del reviews_data['reviews'][i]
            save_json('data/reviews.json', reviews_data)
            flash('Отзыв отклонен и удален', 'success')
            return redirect(url_for('admin.reviews'))

    flash('Отзыв не найден', 'danger')
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/menu')
@admin_required
def menu():
    """Управление меню"""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))

    menu_items = get_menu_items(date=date)

    return render_template('admin/menu.html',
                           menu_items=menu_items,
                           selected_date=date)


@admin_bp.route('/add_menu_item', methods=['POST'])
@admin_required
def add_menu_item():
    """Добавление блюда в меню"""
    date = request.form.get('date')
    meal_type = request.form.get('type')
    name = request.form.get('name')
    description = request.form.get('description')
    price = int(request.form.get('price', 0))
    calories = int(request.form.get('calories', 0))

    allergens = request.form.get('allergens', '')
    allergens_list = [a.strip() for a in allergens.split(',') if a.strip()]

    contains = request.form.get('contains', '')
    contains_list = [c.strip() for c in contains.split(',') if c.strip()]

    new_item = {
        'date': date,
        'type': meal_type,
        'name': name,
        'description': description,
        'price': price,
        'calories': calories,
        'allergens': allergens_list,
        'contains': contains_list,
        'available': True,
        'preparation_time': '20 мин'
    }

    from data_manager import add_menu_item as dm_add_menu_item
    dm_add_menu_item(new_item)
    flash('Блюдо добавлено в меню', 'success')
    return redirect(url_for('admin.menu') + f'?date={date}')


@admin_bp.route('/toggle_menu_item/<int:item_id>')
@admin_required
def toggle_menu_item(item_id):
    """Включение/выключение блюда"""
    menu_item = get_menu_item_by_id(item_id)

    if menu_item:
        from data_manager import update_menu_item
        update_menu_item(item_id, {'available': not menu_item.get('available', True)})
        status = 'доступно' if not menu_item.get('available', True) else 'недоступно'
        flash(f'Блюдо теперь {status}', 'success')
    else:
        flash('Блюдо не найдено', 'danger')

    return redirect(request.referrer or url_for('admin.menu'))


"""
1. Условия
Современные школы нуждаются в удобных и прозрачных
инструментах для организации питания учащихся. Использование
бумажных журналов, талонов и устаревших систем учета не позволяет
эффективно контролировать процесс, оперативно анализировать данные и
обеспечивать безопасность.
Для решения этой задачи предлагается разработать веб-приложение
– автоматизированную информационную систему школьного питания.
Система должна:
● позволять учащимся авторизоваться, просматривать меню завтраков
и обедов, оплачивать питание (разово или абонементом), указывать
аллергены и другие пищевые особенности, оставлять отзывы;
● предоставлять сотрудникам столовой интерфейс для учета
выданных блюд, контроля остатков продуктов и оформления заявок
на закупки;
● обеспечивать администраторам доступ к статистике оплат и
посещаемости, согласованию заявок на закупку и формированию
отчетности.
Реализация веб-приложения позволит повысить эффективность работы
школьной столовой и улучшить качество обслуживания.
2. Техническое задание
Требуется разработать веб-приложение для учёта и контроля питания в
школьной столовой. Приложение должно предоставлять различные
уровни доступа для пользователей и администраторов, поддерживать
оплату питания и обратную связь.
Необходимо предусмотреть роли с уровнями доступа:
● ученик;
● повар;
МОСКОВСКАЯ ПРЕДПРОФЕССИОНАЛЬНАЯ
ОЛИМПИАДА ШКОЛЬНИКОВ
Профиль «Информационные технологии»
Командный кейс No 2 «Управление столовой»
● администратор.
Обязательная функциональность для ученика:
● регистрация и авторизация;
● просмотр меню завтраков и обедов;
● оплата питания (разовый платеж или абонемент);
● отметка о получении питания;
● указание пищевых аллергий и предпочтений;
● оставление отзывов о блюдах.
Обязательная функциональность для повара:
● авторизация в системе;
● учет выданных завтраков и обедов;
● контроль остатков продуктов и готовых блюд;
● внесение заявок на закупку продуктов.
Обязательная функциональность для администратора:
● авторизация в системе;
● просмотр статистики оплат и посещаемости;
● согласование заявок на закупки;
● формирование отчетов по питанию и затратам.
Дополнительная функциональность:
● модуль уведомлений для учеников и сотрудников.
3. Рекомендации к выполнению
● Использовать систему управления базами данных (СУБД) для
хранения данных. Выбор СУБД не регламентируется.
● Рекомендуется применять клиент-серверную архитектуру.
● Использовать систему контроля версий для ведения проекта.
● Предусмотреть автоматизированную установку приложения на
целевой машине.
МОСКОВСКАЯ ПРЕДПРОФЕССИОНАЛЬНАЯ
ОЛИМПИАДА ШКОЛЬНИКОВ
Профиль «Информационные технологии»
Командный кейс No 2 «Управление столовой»
● Уделить внимание вопросам безопасности (персональные данные и
платежи).
4. Требования к документации
● Титульный лист (с указанием названия кейса и перечислением
членов команды).
● Обоснование выбора языка программирования и используемых
программных средств.
● Структурная и функциональная схемы программного продукта.
● Блок-схема работы основного алгоритма.
● Описание особенностей и аргументация выбранного типа СУБД.
● Схема базы данных.
● Программный код (ссылка на репозиторий), файл README должен
включать:
○ краткое описание проекта;
○ инструкцию по установке/развертыванию;
○ ссылку на видеоролик.
МОСКОВСКАЯ ПРЕДПРОФЕССИОНАЛЬНАЯ
ОЛИМПИАДА ШКОЛЬНИКОВ
Профиль «Информационные технологии»
Командный кейс No 2 «Управление столовой»
5. Требования к видеоролику
● Видеоролик должен демонстрировать функционирование
разработанного программного продукта в соответствии с
регламентом испытаний.
● На видео или записи экрана необходимо продемонстрировать
выполнение каждого испытания, описанного в регламенте, в
соответствии с условиями.
● Видео должно однозначно подтверждать авторство участников (во
время записи ролика необходимо четко произнести название
команды, ФИО участников, номер школы, ФИО руководителя).
● Видеоролик необходимо разместить на стороннем видеохостинге
(«ВКонтакте», Rutube и др.)
6. Регламент испытаний
Испытания должны включать проверку всех функциональных требований,
в том числе:
● регистрация и авторизация пользователей;
● оформление оплаты учеником (разовый платеж и абонемент);
● отметка учеником о получении питания;
● учет выданных блюд поваром;
● добавление заявки на закупку продуктов поваром;
● согласование заявки администратором;
● формирование отчета администратором о питании и затратах;
● тестирование обработки исключительных ситуаций (например,
повторная отметка питания учеником или отсутствие достаточного
количества продуктов).

 используй flask, html, css, bootstrap, json (не используй базы данных) (do not use javascript) в первую очередь концентрируйся на функционале а не на деталях

school_canteen/
│
├── app.py                  # Основной файл Flask
├── config.py              # Конфигурация приложения
├── auth.py               # Аутентификация и авторизация
├── data_manager.py       # Работа с JSON-файлами
├── student_routes.py     # Роуты для ученика
├── cook_routes.py        # Роуты для повара
├── admin_routes.py       # Роуты для администратора
│
├── data/                 # JSON-файлы с данными
│   ├── users.json
│   ├── menu.json
│   ├── orders.json
│   ├── inventory.json
│   ├── purchase_requests.json
│   └── reviews.json
|   ____payments.json
│
├── templates/            # HTML шаблоны
│   ├── base.html         # Базовый шаблон
│   ├── login.html
│   ├── register.html, index.html
│   │
│   ├── student/          # Шаблоны для ученика
│   │   ├── dashboard.html
│   │   ├── menu.html
│   │   └── profile.html, my_reviews.html, orders.html, review.html
│   │
│   ├── cook/             # Шаблоны для повара
│   │   ├── dashboard.html
│   │   └── inventory.html, menu.html
│   │
│   └── admin/            # Шаблоны для администратора
│       ├── dashboard.html
│       └── reports.html, dashboard.html, menu.html, requests.html, reviews.html
│
└── static/               # Статические файлы
    ├── css/
    │   └── style.css
    └── images/
    
1. Условия
Современные школы нуждаются в удобных и прозрачных
инструментах для организации питания учащихся. Использование
бумажных журналов, талонов и устаревших систем учета не позволяет
эффективно контролировать процесс, оперативно анализировать данные и
обеспечивать безопасность.
Для решения этой задачи предлагается разработать веб-приложение
– автоматизированную информационную систему школьного питания.
Система должна:
● позволять учащимся авторизоваться, просматривать меню завтраков
и обедов, оплачивать питание (разово или абонементом), указывать
аллергены и другие пищевые особенности, оставлять отзывы;
● предоставлять сотрудникам столовой интерфейс для учета
выданных блюд, контроля остатков продуктов и оформления заявок
на закупки;
● обеспечивать администраторам доступ к статистике оплат и
посещаемости, согласованию заявок на закупку и формированию
отчетности.
Реализация веб-приложения позволит повысить эффективность работы
школьной столовой и улучшить качество обслуживания.
2. Техническое задание
Требуется разработать веб-приложение для учёта и контроля питания в
школьной столовой. Приложение должно предоставлять различные
уровни доступа для пользователей и администраторов, поддерживать
оплату питания и обратную связь.
Необходимо предусмотреть роли с уровнями доступа:
● ученик;
● повар;
МОСКОВСКАЯ ПРЕДПРОФЕССИОНАЛЬНАЯ
ОЛИМПИАДА ШКОЛЬНИКОВ
Профиль «Информационные технологии»
Командный кейс No 2 «Управление столовой»
● администратор.
Обязательная функциональность для ученика:
● регистрация и авторизация;
● просмотр меню завтраков и обедов;
● оплата питания (разовый платеж или абонемент);
● отметка о получении питания;
● указание пищевых аллергий и предпочтений;
● оставление отзывов о блюдах.
Обязательная функциональность для повара:
● авторизация в системе;
● учет выданных завтраков и обедов;
● контроль остатков продуктов и готовых блюд;
● внесение заявок на закупку продуктов.
Обязательная функциональность для администратора:
● авторизация в системе;
● просмотр статистики оплат и посещаемости;
● согласование заявок на закупки;
● формирование отчетов по питанию и затратам.
Дополнительная функциональность:
● модуль уведомлений для учеников и сотрудников.
3. Рекомендации к выполнению
● Использовать систему управления базами данных (СУБД) для
хранения данных. Выбор СУБД не регламентируется.
● Рекомендуется применять клиент-серверную архитектуру.
● Использовать систему контроля версий для ведения проекта.
● Предусмотреть автоматизированную установку приложения на
целевой машине.
МОСКОВСКАЯ ПРЕДПРОФЕССИОНАЛЬНАЯ
ОЛИМПИАДА ШКОЛЬНИКОВ
Профиль «Информационные технологии»
Командный кейс No 2 «Управление столовой»
● Уделить внимание вопросам безопасности (персональные данные и
платежи).
4. Требования к документации
● Титульный лист (с указанием названия кейса и перечислением
членов команды).
● Обоснование выбора языка программирования и используемых
программных средств.
● Структурная и функциональная схемы программного продукта.
● Блок-схема работы основного алгоритма.
● Описание особенностей и аргументация выбранного типа СУБД.
● Схема базы данных.
● Программный код (ссылка на репозиторий), файл README должен
включать:
○ краткое описание проекта;
○ инструкцию по установке/развертыванию;
○ ссылку на видеоролик.
МОСКОВСКАЯ ПРЕДПРОФЕССИОНАЛЬНАЯ
ОЛИМПИАДА ШКОЛЬНИКОВ
Профиль «Информационные технологии»
Командный кейс No 2 «Управление столовой»
5. Требования к видеоролику
● Видеоролик должен демонстрировать функционирование
разработанного программного продукта в соответствии с
регламентом испытаний.
● На видео или записи экрана необходимо продемонстрировать
выполнение каждого испытания, описанного в регламенте, в
соответствии с условиями.
● Видео должно однозначно подтверждать авторство участников (во
время записи ролика необходимо четко произнести название
команды, ФИО участников, номер школы, ФИО руководителя).
● Видеоролик необходимо разместить на стороннем видеохостинге
(«ВКонтакте», Rutube и др.)
6. Регламент испытаний
Испытания должны включать проверку всех функциональных требований,
в том числе:
● регистрация и авторизация пользователей;
● оформление оплаты учеником (разовый платеж и абонемент);
● отметка учеником о получении питания;
● учет выданных блюд поваром;
● добавление заявки на закупку продуктов поваром;
● согласование заявки администратором;
● формирование отчета администратором о питании и затратах;
● тестирование обработки исключительных ситуаций (например,
повторная отметка питания учеником или отсутствие достаточного
количества продуктов).

 используй flask, html, css, bootstrap, json (не используй базы данных) (do not use javascript) в первую очередь концентрируйся на функционале а не на деталях

обдумай перед тем как эту штуки делать (надо понять задачу и потом разделить на подзадачи), не делай все в одном файле и сделай базовый функционал, потом напиши дальнейший план


"""