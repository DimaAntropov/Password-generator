from flask import Flask, render_template, request, redirect, url_for, session
import random
import string
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_strong_and_unique_secret_key'

# Пути к файлам
USER_FILE_PATH = r'\\192.168.3.250\Veda\3 курс\ИСП 32\Разработка web приложения\Антропов и Леконцев\генерация поролей\User.txt'
PASSWORD_FILE_PATH = r'\\192.168.3.250\Veda\3 курс\ИСП 32\Разработка web приложения\Антропов и Леконцев\генерация поролей\Pasword.txt'

# Изначальные пользователи
USER_CREDENTIALS = {
    "Танк": "Железный"
}

# Декоратор для проверки входа
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Функции для сохранения в файлы
def save_user_to_file(username, password):
    with open(USER_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(f'{username}:{password}\n')

def save_password_to_file(username, password):
    with open(PASSWORD_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(f'{username}:{password}\n')

# Генерация пароля
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
        return "Ошибка: выберите хотя бы один тип символов."
    length = max(4, min(length, 128))
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    password = None
    username = session.get('username', 'Пользователь')
    length = 12
    use_lowercase = True
    use_uppercase = True
    use_digits = True
    use_symbols = False

    if request.method == 'POST':
        try:
            length = int(request.form.get('length'))
            use_lowercase = 'lowercase' in request.form
            use_uppercase = 'uppercase' in request.form
            use_digits = 'digits' in request.form
            use_symbols = 'symbols' in request.form

            if not (use_lowercase or use_uppercase or use_digits or use_symbols):
                password = "Ошибка: выберите хотя бы один тип символов."
            else:
                password = generate_password(length, use_lowercase, use_uppercase, use_digits, use_symbols)
                # Сохраняем сгенерированный пароль в файл
                save_password_to_file(username, password)
        except (ValueError, TypeError):
            password = "Ошибка: пожалуйста, введите действительную длину."

    return render_template(
        'index.html',
        password=password,
        length=length,
        use_lowercase=use_lowercase,
        use_uppercase=use_uppercase,
        use_digits=use_digits,
        use_symbols=use_symbols,
        username=username
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            error = 'Неправильный логин или пароль.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if username in USER_CREDENTIALS:
            error = 'Этот логин уже занят.'
        elif password != confirm_password:
            error = 'Пароли не совпадают.'
        else:
            # Сохраняем в файлы
            save_user_to_file(username, password)
            USER_CREDENTIALS[username] = password
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
    return render_template('register.html', error=error)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5100)
