import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuración de la base de datos (Render usa DATABASE_URL)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///restaurant.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------- MODELOS -------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    restaurants = db.relationship('Restaurant', backref='owner', lazy=True)

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tables = db.relationship('Table', backref='restaurant', lazy=True)
    items = db.relationship('MenuItem', backref='restaurant', lazy=True)

class Table(db.Model):
    __tablename__ = 'tables'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    table_number = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    reservations = db.relationship('Reservation', backref='table', lazy=True)

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    price = db.Column(db.Numeric(10, 2), nullable=False)

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    reservations = db.relationship('Reservation', backref='customer', lazy=True)

class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    reservation_datetime = db.Column(db.DateTime, nullable=False)

# ------------------- RUTAS API -------------------

@app.route('/')
def home():
    return 'API de restaurantes funcionando'

# ----- USUARIOS (RESTAURANTE) -----
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('email'):
        return jsonify({'error': 'username y email son obligatorios'}), 400
    user = User(username=data['username'], email=data['email'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'id': user.id, 'username': user.username, 'email': user.email}), 201

@app.route('/api/users', methods=['GET'])
def list_users():
    users = User.query.all()
    return jsonify([{'id': u.id, 'username': u.username, 'email': u.email} for u in users])

# ----- RESTAURANTES -----
@app.route('/api/restaurants', methods=['POST'])
def create_restaurant():
    data = request.get_json()
    if not data or not data.get('name') or not data.get('user_id'):
        return jsonify({'error': 'name y user_id son obligatorios'}), 400
    user = User.query.get(data['user_id'])
    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    restaurant = Restaurant(name=data['name'], user_id=data['user_id'])
    db.session.add(restaurant)
    db.session.commit()
    return jsonify({'id': restaurant.id, 'name': restaurant.name}), 201

@app.route('/api/restaurants', methods=['GET'])
def list_restaurants():
    user_id = request.args.get('user_id', type=int)
    query = Restaurant.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    restaurants = query.all()
    return jsonify([{'id': r.id, 'name': r.name, 'user_id': r.user_id} for r in restaurants])

# ----- MESAS -----
@app.route('/api/tables', methods=['POST'])
def create_table():
    data = request.get_json()
    if not data or not data.get('restaurant_id') or not data.get('table_number') or not data.get('capacity'):
        return jsonify({'error': 'restaurant_id, table_number y capacity son obligatorios'}), 400
    if not Restaurant.query.get(data['restaurant_id']):
        return jsonify({'error': 'Restaurante no encontrado'}), 404
    table = Table(
        restaurant_id=data['restaurant_id'],
        table_number=data['table_number'],
        capacity=data['capacity']
    )
    db.session.add(table)
    db.session.commit()
    return jsonify({'id': table.id, 'table_number': table.table_number, 'capacity': table.capacity}), 201

@app.route('/api/tables', methods=['GET'])
def list_tables():
    restaurant_id = request.args.get('restaurant_id', type=int)
    if not restaurant_id:
        return jsonify({'error': 'restaurant_id es obligatorio'}), 400
    tables = Table.query.filter_by(restaurant_id=restaurant_id).all()
    return jsonify([{'id': t.id, 'table_number': t.table_number, 'capacity': t.capacity} for t in tables])

# ----- ITEMS DEL MENÚ -----
@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.get_json()
    if not data or not data.get('restaurant_id') or not data.get('name') or not data.get('price'):
        return jsonify({'error': 'restaurant_id, name y price son obligatorios'}), 400
    if not Restaurant.query.get(data['restaurant_id']):
        return jsonify({'error': 'Restaurante no encontrado'}), 404
    item = MenuItem(
        restaurant_id=data['restaurant_id'],
        name=data['name'],
        description=data.get('description', ''),
        price=data['price']
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'id': item.id, 'name': item.name, 'price': float(item.price)}), 201

@app.route('/api/items', methods=['GET'])
def list_items():
    restaurant_id = request.args.get('restaurant_id', type=int)
    if not restaurant_id:
        return jsonify({'error': 'restaurant_id es obligatorio'}), 400
    items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
    return jsonify([{
        'id': i.id, 'name': i.name,
        'description': i.description, 'price': float(i.price)
    } for i in items])

# ----- CLIENTES -----
@app.route('/api/customers', methods=['POST'])
def create_customer():
    data = request.get_json()
    if not data or not data.get('name') or not data.get('email'):
        return jsonify({'error': 'name y email son obligatorios'}), 400
    if Customer.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'El email ya está registrado'}), 409
    customer = Customer(name=data['name'], email=data['email'])
    db.session.add(customer)
    db.session.commit()
    return jsonify({'id': customer.id, 'name': customer.name, 'email': customer.email}), 201

@app.route('/api/customers', methods=['GET'])
def list_customers():
    customers = Customer.query.all()
    return jsonify([{'id': c.id, 'name': c.name, 'email': c.email} for c in customers])

# ----- RESERVAS -----
@app.route('/api/reservations', methods=['POST'])
def create_reservation():
    data = request.get_json()
    required = ['table_id', 'customer_id', 'reservation_datetime']
    if not data or any(k not in data for k in required):
        return jsonify({'error': 'table_id, customer_id y reservation_datetime son obligatorios'}), 400
    if not Table.query.get(data['table_id']):
        return jsonify({'error': 'Mesa no encontrada'}), 404
    if not Customer.query.get(data['customer_id']):
        return jsonify({'error': 'Cliente no encontrado'}), 404
    try:
        dt = datetime.fromisoformat(data['reservation_datetime'])
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido. Usa ISO 8601 (YYYY-MM-DDTHH:MM)'}), 400
    # Comprobamos que no exista otra reserva para la misma mesa y hora
    existe = Reservation.query.filter_by(
        table_id=data['table_id'],
        reservation_datetime=dt
    ).first()
    if existe:
        return jsonify({'error': 'La mesa ya está reservada en ese horario'}), 409
    reservation = Reservation(
        table_id=data['table_id'],
        customer_id=data['customer_id'],
        reservation_datetime=dt
    )
    db.session.add(reservation)
    db.session.commit()
    return jsonify({'id': reservation.id, 'message': 'Reserva creada'}), 201

@app.route('/api/reservations', methods=['GET'])
def list_reservations():
    restaurant_id = request.args.get('restaurant_id', type=int)
    date_str = request.args.get('date')  # YYYY-MM-DD
    query = Reservation.query.join(Table)
    if restaurant_id:
        query = query.filter(Table.restaurant_id == restaurant_id)
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido. Usa YYYY-MM-DD'}), 400
        query = query.filter(db.func.date(Reservation.reservation_datetime) == date_obj)
    reservations = query.all()
    result = []
    for r in reservations:
        result.append({
            'id': r.id,
            'table_id': r.table_id,
            'table_number': r.table.table_number,
            'customer_id': r.customer_id,
            'customer_name': r.customer.name,
            'reservation_datetime': r.reservation_datetime.isoformat()
        })
    return jsonify(result)

# ------------------- INICIALIZACIÓN -------------------
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)