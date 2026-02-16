from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from data_manager import get_user_by_username, verify_password, add_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = get_user_by_username(username)

        if user and verify_password(password, user['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']

            flash('Вы успешно вошли в систему!', 'success')

            # Перенаправляем в зависимости от роли
            if user['role'] == 'student':
                return redirect(url_for('student.dashboard'))
            elif user['role'] == 'cook':
                return redirect(url_for('cook.dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        class_name = request.form.get('class')

        # Проверяем пароли
        if password != confirm_password:
            flash('Пароли не совпадают', 'danger')
            return render_template('register.html')

        # Проверяем, что роль допустима
        if role not in ['student', 'cook']:
            flash('Недопустимая роль', 'danger')
            return render_template('register.html')

        # Добавляем пользователя
        if add_user(username, password, role, full_name, email):
            flash('Регистрация успешна! Теперь войдите в систему.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Пользователь с таким именем уже существует', 'danger')

    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))