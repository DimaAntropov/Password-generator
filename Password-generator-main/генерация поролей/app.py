from flask import Flask, render_template, request, redirect, url_for, session
import random
import string
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_strong_and_unique_secret_key'  # В реальном проекте ключ должен быть сложным

# Временная база данных пользователей
USER_CREDENTIALS = {
    "Танк": "Железный"
}


# --- Декоратор авторизации ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


# --- Генерация пароля ---
def generate_password(length, use_lowercase, use_uppercase, use_digits, use_symbols):
    characters = ''
    if use_lowercase: characters += string.ascii_lowercase
    if use_uppercase: characters += string.ascii_uppercase
    if use_digits:    characters += string.digits
    if use_symbols:   characters += string.punctuation

    if not characters: return None
    length = max(4, min(length, 128))
    return ''.join(random.choice(characters) for i in range(length))


# --- Главная страница (Генератор) ---
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    password = None
    username = session.get('username')

    # Настройки по умолчанию
    length = 12
    use_lowercase = True
    use_uppercase = True
    use_digits = True
    use_symbols = False

    if request.method == 'POST':
        # Если нажата кнопка очистки истории
        if 'clear_history' in request.form:
            session.pop('history', None)
        else:
            # Генерация пароля
            try:
                length = int(request.form.get('length', 12))
                use_lowercase = 'lowercase' in request.form
                use_uppercase = 'uppercase' in request.form
                use_digits = 'digits' in request.form
                use_symbols = 'symbols' in request.form

                if (use_lowercase or use_uppercase or use_digits or use_symbols):
                    password = generate_password(length, use_lowercase, use_uppercase, use_digits, use_symbols)

                    # === СОХРАНЕНИЕ В ИСТОРИЮ ===
                    if password:
                        # Получаем текущую историю из сессии или создаем пустой список
                        history = session.get('history', [])
                        # Добавляем новый пароль в начало
                        history.insert(0, password)
                        # Оставляем только последние 5 паролей
                        session['history'] = history[:5]
                        session.modified = True  # Сообщаем Flask, что сессия изменилась
            except:
                pass

    # Получаем историю для отображения
    history = session.get('history', [])

    return render_template('index.html', password=password, history=history, length=length,
                           use_lowercase=use_lowercase, use_uppercase=use_uppercase,
                           use_digits=use_digits, use_symbols=use_symbols, username=username)


# --- Вход (Login) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    # Получаем историю из сессии (она доступна даже если пользователь не вошел)
    history = session.get('history', [])

    if request.method == 'POST':
        # Обработка кнопки очистки истории на странице входа
        if 'clear_history' in request.form:
            session.pop('history', None)
            return redirect(url_for('login'))

        username = request.form.get('username')
        password = request.form.get('password')

        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            error = 'Неправильный логин или пароль.'

    return render_template('login.html', error=error, history=history)


# --- Выход ---
@app.route('/logout')
def logout():
    # ВАЖНО: Удаляем только данные авторизации, но оставляем 'history'
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))


# --- Регистрация ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if username in USER_CREDENTIALS:
            error = 'Логин занят.'
        elif password != confirm:
            error = 'Пароли не совпадают.'
        else:
            USER_CREDENTIALS[username] = password
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
    return render_template('register.html', error=error)


if __name__ == '__main__':
    app.run(debug=True)