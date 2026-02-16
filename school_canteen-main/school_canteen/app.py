from flask import Flask, render_template, session, redirect, url_for, request, flash
from auth import auth_bp
from student_routes import student_bp
from cook_routes import cook_bp
from admin_routes import admin_bp
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Регистрация Blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(cook_bp, url_prefix='/cook')
app.register_blueprint(admin_bp, url_prefix='/admin')


# Контекстный процессор для передачи темы во все шаблоны
@app.context_processor
def inject_theme():
    theme = session.get('theme', 'light')
    return {'theme': theme}


@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'student':
            return redirect(url_for('student.dashboard'))
        elif role == 'cook':
            return redirect(url_for('cook.dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin.dashboard'))
    return render_template('index.html')


@app.route('/toggle-theme', methods=['POST'])
def toggle_theme():
    current_theme = session.get('theme', 'light')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    session['theme'] = new_theme
    flash(f'Тема изменена на {"темную" if new_theme == "dark" else "светлую"}', 'info')

    # Возвращаемся на предыдущую страницу или на главную
    referrer = request.referrer
    if referrer and referrer.startswith(request.host_url):
        return redirect(referrer)
    return redirect(url_for('index'))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Простая страница настроек пользователя (доступна только для авторизованных)."""
    if 'user_id' not in session:
        flash('Пожалуйста, войдите в систему', 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # Поддерживаем изменение темы со страницы настроек
        new_theme = request.form.get('theme')
        if new_theme in ('light', 'dark'):
            session['theme'] = new_theme
            flash('Тема сохранена', 'success')
        else:
            flash('Неверное значение настройки', 'danger')
        return redirect(url_for('settings'))

    return render_template('settings.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)