from flask import Flask, render_template, request, redirect, session, url_for, Response
from functools import wraps
import sqlite3
from collections import Counter
from dotenv import load_dotenv
import os

app = Flask(__name__)
app.secret_key = 'super-secret-key-2025'

# Загрузка переменных из .env
load_dotenv()

# Данные администратора (из переменных окружения)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '')

# ============= РАСШИРЕННОЕ МЕНЮ (16 позиций, 5 категорий) =============
menu = [
    # ПИЦЦА
    {"id": 1, "name": "Пицца Маргарита", "price": 450, "category": "Пицца", "category_ru": "🍕 Пицца"},
    {"id": 2, "name": "Пицца Пепперони", "price": 520, "category": "Пицца", "category_ru": "🍕 Пицца"},
    {"id": 3, "name": "Пицца 4 сыра", "price": 580, "category": "Пицца", "category_ru": "🍕 Пицца"},
    {"id": 4, "name": "Пицца Гавайская", "price": 550, "category": "Пицца", "category_ru": "🍕 Пицца"},
    {"id": 5, "name": "Пицца Мясная", "price": 620, "category": "Пицца", "category_ru": "🍕 Пицца"},
    
    # САЛАТЫ
    {"id": 6, "name": "Цезарь с курицей", "price": 350, "category": "Салаты", "category_ru": "🥗 Салаты"},
    {"id": 7, "name": "Греческий салат", "price": 300, "category": "Салаты", "category_ru": "🥗 Салаты"},
    {"id": 8, "name": "Оливье", "price": 280, "category": "Салаты", "category_ru": "🥗 Салаты"},
    
    # НАПИТКИ
    {"id": 9, "name": "Кола 0.5л", "price": 120, "category": "Напитки", "category_ru": "🥤 Напитки"},
    {"id": 10, "name": "Сок апельсиновый", "price": 150, "category": "Напитки", "category_ru": "🥤 Напитки"},
    {"id": 11, "name": "Лимонад домашний", "price": 180, "category": "Напитки", "category_ru": "🥤 Напитки"},
    {"id": 12, "name": "Морс клюквенный", "price": 160, "category": "Напитки", "category_ru": "🥤 Напитки"},
    
    # ДЕСЕРТЫ
    {"id": 13, "name": "Чизкейк Нью-Йорк", "price": 290, "category": "Десерты", "category_ru": "🍰 Десерты"},
    {"id": 14, "name": "Тирамису", "price": 320, "category": "Десерты", "category_ru": "🍰 Десерты"},
    
    # ЗАКУСКИ
    {"id": 15, "name": "Картофель фри", "price": 180, "category": "Закуски", "category_ru": "🍟 Закуски"},
    {"id": 16, "name": "Куриные наггетсы", "price": 250, "category": "Закуски", "category_ru": "🍟 Закуски"},
]

def get_db_connection():
    conn = sqlite3.connect('food_delivery.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных с правильной структурой"""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            order_items TEXT NOT NULL,
            total_price INTEGER NOT NULL,
            status TEXT DEFAULT 'Новый',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            comment TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()

# ============= АДМИН АВТОРИЗАЦИЯ (через сессию) =============
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session.permanent = False
            return redirect(url_for('admin'))
        else:
            error = "Неверный логин или пароль!"
    
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# ============= ГЛАВНАЯ =============
@app.route('/')
def index():
    cart_count = len(session.get('cart', []))
    categories = {}
    for item in menu:
        if item['category'] not in categories:
            categories[item['category']] = item['category_ru']
    return render_template('index.html', menu=menu, categories=categories, cart_count=cart_count)

@app.route('/category/<category>')
def category(category):
    cart_count = len(session.get('cart', []))
    filtered_menu = [item for item in menu if item['category'] == category]
    categories = {}
    for item in menu:
        if item['category'] not in categories:
            categories[item['category']] = item['category_ru']
    return render_template('index.html', menu=filtered_menu, categories=categories, 
                          active_category=category, cart_count=cart_count)

# ============= КОРЗИНА =============
@app.route('/add_to_cart/<int:item_id>')
def add_to_cart(item_id):
    if 'cart' not in session:
        session['cart'] = []
    session['cart'].append(item_id)
    session.modified = True
    return redirect(request.referrer or url_for('index'))

@app.route('/remove_from_cart/<int:item_id>')
def remove_from_cart(item_id):
    if 'cart' in session and item_id in session['cart']:
        session['cart'].remove(item_id)
        session.modified = True
    return redirect(request.referrer or url_for('cart'))

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    session.modified = True
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    cart_items = []
    total = 0
    
    if 'cart' in session:
        cart_counter = Counter(session['cart'])
        for item_id, quantity in cart_counter.items():
            item = next((x for x in menu if x['id'] == item_id), None)
            if item:
                cart_items.append({
                    'id': item['id'],
                    'name': item['name'],
                    'price': item['price'],
                    'quantity': quantity,
                    'total': item['price'] * quantity
                })
                total += item['price'] * quantity
    
    cart_count = len(session.get('cart', []))
    return render_template('cart.html', items=cart_items, total=total, cart_count=cart_count)

# ============= ОФОРМЛЕНИЕ ЗАКАЗА =============
@app.route('/order')
def order():
    cart_count = len(session.get('cart', []))
    if cart_count == 0:
        return redirect(url_for('cart'))
    return render_template('order.html', cart_count=cart_count)

@app.route('/place_order', methods=['POST'])
def place_order():
    name = request.form['name']
    phone = request.form['phone']
    address = request.form['address']
    comment = request.form.get('comment', '')
    
    cart_items = []
    total = 0
    if 'cart' in session:
        for item_id in session['cart']:
            item = next((x for x in menu if x['id'] == item_id), None)
            if item:
                cart_items.append(item['name'])
                total += item['price']
    
    conn = get_db_connection()
    cursor = conn.execute('''
        INSERT INTO orders (customer_name, customer_phone, customer_address, order_items, total_price, comment)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, phone, address, ', '.join(cart_items), total, comment))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    session.pop('cart', None)
    session.modified = True
    
    return render_template('order_success.html', order_id=order_id)

# ============= АДМИН-ПАНЕЛЬ =============
@app.route('/admin')
@admin_required
def admin():
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders ORDER BY order_date DESC').fetchall()
    conn.close()
    cart_count = len(session.get('cart', []))
    return render_template('admin.html', orders=orders, cart_count=cart_count)

@app.route('/update_status/<int:order_id>/<status>')
@admin_required
def update_status(order_id, status):
    conn = get_db_connection()
    conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)