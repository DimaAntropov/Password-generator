from flask import Flask, render_template, request, redirect, url_for, session
import random
import string
from functools import wraps
import sqlite3

# импортируем функцию инициализации БД и путь к файлу БД
from init_db import init_db, DB_PATH

app = Flask(__name__)
app.secret_key = 'your_strong_and_unique_secret_key'  # Поменяй на свой


# --- Подключение к SQLite ---
def get_db():
    """Получить соединение с SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # строки как словари
    return conn


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
    if use_lowercase:
        characters += string.ascii_lowercase
    if use_uppercase:
        characters += string.ascii_uppercase
    if use_digits:
        characters += string.digits
    if use_symbols:
        characters += string.punctuation

    if not characters:
        return None
    length = max(4, min(length, 128))
    return ''.join(random.choice(characters) for _ in range(length))


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
            try:
                length = int(request.form.get('length', 12))
            except ValueError:
                length = 12

            use_lowercase = 'lowercase' in request.form
            use_uppercase = 'uppercase' in request.form
            use_digits = 'digits' in request.form
            use_symbols = 'symbols' in request.form

            # данные для сохранения пароля сервиса
            service = request.form.get('service', '').strip()
            service_login = request.form.get('service_login', '').strip()

            if use_lowercase or use_uppercase or use_digits or use_symbols:
                password = generate_password(length, use_lowercase, use_uppercase, use_digits, use_symbols)

                if password:
                    # --- История в сессии (как у тебя было) ---
                    history = session.get('history', [])
                    history.insert(0, password)
                    session['history'] = history[:5]
                    session.modified = True

                    # --- Сохранение пароля для сервиса в БД ---
                    # Если указано название сервиса
                    if service:
                        user_id = session.get('user_id')
                        if user_id:
                            conn = get_db()
                            cur = conn.cursor()
                            cur.execute(
                                """
                                INSERT INTO service_passwords (user_id, service, login, password)
                                VALUES (?, ?, ?, ?)
                                """,
                                (user_id, service, service_login, password)
                            )
                            conn.commit()
                            conn.close()

    # Получаем историю для отображения
    history = session.get('history', [])

    return render_template(
        'index.html',
        password=password,
        history=history,
        length=length,
        use_lowercase=use_lowercase,
        use_uppercase=use_uppercase,
        use_digits=use_digits,
        use_symbols=use_symbols,
        username=username
    )


# --- Страница со списком сохранённых паролей ---
@app.route('/passwords')
@login_required
def password_manager():
    user_id = session.get('user_id')
    username = session.get('username')

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, service, login, password, created_at
        FROM service_passwords
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,)
    )
    entries = cur.fetchall()
    conn.close()

    return render_template('password_manager.html', entries=entries, username=username)


# --- Вход (Login) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    # История паролей в сессии (доступна и без входа)
    history = session.get('history', [])

    if request.method == 'POST':
        # Кнопка очистки истории
        if 'clear_history' in request.form:
            session.pop('history', None)
            return redirect(url_for('login'))

        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        conn.close()

        # В реальном приложении здесь нужно использовать хэширование паролей!
        if user and user['password'] == password:
            session['logged_in'] = True
            session['username'] = username
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        else:
            error = 'Неправильный логин или пароль.'

    return render_template('login.html', error=error, history=history)


# --- Выход ---
@app.route('/logout')
def logout():
    # Очищаем данные авторизации
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('user_id', None)
    # history оставляем
    return redirect(url_for('login'))


# --- Регистрация ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if password != confirm:
            error = 'Пароли не совпадают.'
        else:
            conn = get_db()
            cur = conn.cursor()

            # Проверка: есть ли уже такой логин
            cur.execute("SELECT id FROM users WHERE username = ?", (username,))
            existing = cur.fetchone()

            if existing:
                error = 'Логин занят.'
                conn.close()
            else:
                cur.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, password)
                )
                conn.commit()
                user_id = cur.lastrowid
                conn.close()

                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = user_id
                return redirect(url_for('index'))

    return render_template('register.html', error=error)


if __name__ == '__main__':
    # Перед запуском приложения убеждаемся, что БД и таблицы существуют
    init_db()
    app.run(debug=True)