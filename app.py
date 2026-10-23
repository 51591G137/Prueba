"""
Mi Restaurante - backend (Flask + SQLAlchemy)

  /              página de inicio con enlaces a las dos apps
  /restaurante/  app de gestión: usuarios -> restaurantes -> mesas, menú y reservas
  /cliente/      app de clientes: clientes -> restaurantes -> mesas, menú y reservas
  /api/...       API JSON que usan las dos apps
  /health        comprobación de estado (por si quieres usarla en Render)

Primera versión: sin contraseñas ni permisos, a propósito.
"""
import math
import os
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")

# --- Base de datos -----------------------------------------------------------
# En el plan gratuito de Render el disco se borra cada vez que el servicio se
# reinicia o se duerme, así que un SQLite local pierde los datos. Para que
# persistan, crea un Postgres y pon su URL en la variable de entorno DATABASE_URL
# (mira el README). Sin esa variable se usa SQLite: ideal para desarrollar.
db_url = os.environ.get("DATABASE_URL", "").strip()
if db_url.startswith("postgres://"):  # formato antiguo que SQLAlchemy no acepta
    db_url = "postgresql://" + db_url[len("postgres://"):]
if not db_url:
    db_url = "sqlite:///" + os.path.join(BASE_DIR, "app.db")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
db = SQLAlchemy(app)


# --- Modelos (esquema mínimo para esta iteración) -----------------------------
class User(db.Model):
    """Persona que gestiona restaurantes (app de restaurantes)."""
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)


class Customer(db.Model):
    """Persona que reserva mesa (app de clientes)."""
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)


class Restaurant(db.Model):
    __tablename__ = "restaurants"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200))


class RestaurantTable(db.Model):
    """Una mesa del restaurante (la clase no se llama Table para no chocar con db.Table)."""
    __tablename__ = "tables"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False, index=True)
    name = db.Column(db.String(40), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)


class MenuItem(db.Model):
    __tablename__ = "menu_items"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(300))
    price = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False)


class Reservation(db.Model):
    """Una mesa reservada en una franja concreta (fecha y hora)."""
    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    # La propia base de datos impide reservar dos veces la misma mesa a la misma hora.
    __table_args__ = (db.UniqueConstraint("table_id", "date", "time", name="uq_reservation_slot"),)


with app.app_context():
    db.create_all()


# --- Utilidades ----------------------------------------------------------------
class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def as_dict(obj, *fields):
    return {field: getattr(obj, field) for field in fields}


def text_field(data, key, label, max_len, required=True):
    value = data.get(key)
    value = value.strip() if isinstance(value, str) else ""
    if required and not value:
        raise ApiError(f"{label} es obligatorio.")
    if len(value) > max_len:
        raise ApiError(f"{label} no puede superar {max_len} caracteres.")
    return value or None


def int_field(data, key, label, minimum, maximum):
    try:
        value = int(str(data.get(key)).strip())
    except ValueError:
        raise ApiError(f"{label} debe ser un número entero.")
    if not minimum <= value <= maximum:
        raise ApiError(f"{label} debe estar entre {minimum} y {maximum}.")
    return value


def price_field(data):
    try:
        value = float(str(data.get("price")).replace(",", ".").strip())
    except ValueError:
        raise ApiError("El precio debe ser un número, por ejemplo 12.50.")
    if not math.isfinite(value) or not 0 <= value <= 10000:
        raise ApiError("El precio debe estar entre 0 y 10000.")
    return round(value, 2)


def parse_date(value):
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").date()
    except ValueError:
        raise ApiError("La fecha no es válida. Usa el formato AAAA-MM-DD.")


def parse_time(value):
    try:
        return datetime.strptime(str(value or ""), "%H:%M").time()
    except ValueError:
        raise ApiError("La hora no es válida. Usa el formato HH:MM.")


def save(obj):
    db.session.add(obj)
    db.session.commit()
    return obj


@app.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify(error=err.message), err.status


@app.errorhandler(HTTPException)
def handle_http_error(err):
    if request.path.startswith("/api/"):
        message = "No encontrado." if err.code == 404 else err.description
        return jsonify(error=message), err.code
    return err


# --- Páginas ---------------------------------------------------------------------
@app.get("/")
def home():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/restaurante/")
def restaurant_app():
    return send_from_directory(STATIC_DIR, "restaurante.html")


@app.get("/cliente/")
def customer_app():
    return send_from_directory(STATIC_DIR, "cliente.html")


@app.get("/health")
def health():
    return jsonify(status="ok")


# --- API: usuarios y clientes ---------------------------------------------------
@app.get("/api/users")
def list_users():
    return jsonify([as_dict(u, "id", "name") for u in User.query.order_by(User.id)])


@app.post("/api/users")
def create_user():
    user = save(User(name=text_field(body(), "name", "El nombre", 80)))
    return jsonify(as_dict(user, "id", "name")), 201


@app.get("/api/users/<int:user_id>")
def get_user(user_id):
    return jsonify(as_dict(db.get_or_404(User, user_id), "id", "name"))


@app.get("/api/customers")
def list_customers():
    return jsonify([as_dict(c, "id", "name") for c in Customer.query.order_by(Customer.id)])


@app.post("/api/customers")
def create_customer():
    customer = save(Customer(name=text_field(body(), "name", "El nombre", 80)))
    return jsonify(as_dict(customer, "id", "name")), 201


@app.get("/api/customers/<int:customer_id>")
def get_customer(customer_id):
    return jsonify(as_dict(db.get_or_404(Customer, customer_id), "id", "name"))


# --- API: restaurantes ---------------------------------------------------------
RESTAURANT_FIELDS = ("id", "name", "address")


@app.get("/api/users/<int:user_id>/restaurants")
def list_user_restaurants(user_id):
    db.get_or_404(User, user_id)
    rows = Restaurant.query.filter_by(user_id=user_id).order_by(Restaurant.id)
    return jsonify([as_dict(r, *RESTAURANT_FIELDS) for r in rows])


@app.post("/api/users/<int:user_id>/restaurants")
def create_restaurant(user_id):
    db.get_or_404(User, user_id)
    data = body()
    restaurant = save(Restaurant(
        user_id=user_id,
        name=text_field(data, "name", "El nombre", 120),
        address=text_field(data, "address", "La dirección", 200, required=False),
    ))
    return jsonify(as_dict(restaurant, *RESTAURANT_FIELDS)), 201


@app.get("/api/restaurants")
def list_restaurants():
    """Todos los restaurantes (lo usa la app de clientes)."""
    rows = Restaurant.query.order_by(Restaurant.id)
    return jsonify([as_dict(r, *RESTAURANT_FIELDS) for r in rows])


@app.get("/api/restaurants/<int:restaurant_id>")
def get_restaurant(restaurant_id):
    return jsonify(as_dict(db.get_or_404(Restaurant, restaurant_id), *RESTAURANT_FIELDS))


# --- API: mesas -------------------------------------------------------------------
@app.get("/api/restaurants/<int:restaurant_id>/tables")
def list_tables(restaurant_id):
    """Mesas del restaurante. Con ?date=AAAA-MM-DD&time=HH:MM cada mesa indica si está reservada."""
    db.get_or_404(Restaurant, restaurant_id)
    tables = RestaurantTable.query.filter_by(restaurant_id=restaurant_id).order_by(RestaurantTable.id).all()
    result = [as_dict(t, "id", "name", "capacity") for t in tables]

    if request.args.get("date") and request.args.get("time"):
        day = parse_date(request.args["date"])
        hour = parse_time(request.args["time"])
        taken = {
            r.table_id
            for r in Reservation.query.filter(
                Reservation.table_id.in_([t.id for t in tables]),
                Reservation.date == day,
                Reservation.time == hour,
            )
        }
        for table in result:
            table["reserved"] = table["id"] in taken
    return jsonify(result)


@app.post("/api/restaurants/<int:restaurant_id>/tables")
def create_table(restaurant_id):
    db.get_or_404(Restaurant, restaurant_id)
    data = body()
    table = save(RestaurantTable(
        restaurant_id=restaurant_id,
        name=text_field(data, "name", "El nombre de la mesa", 40),
        capacity=int_field(data, "capacity", "La capacidad", 1, 50),
    ))
    return jsonify(as_dict(table, "id", "name", "capacity")), 201


# --- API: menú ------------------------------------------------------------------------
MENU_FIELDS = ("id", "name", "description", "price")


@app.get("/api/restaurants/<int:restaurant_id>/menu")
def list_menu(restaurant_id):
    db.get_or_404(Restaurant, restaurant_id)
    rows = MenuItem.query.filter_by(restaurant_id=restaurant_id).order_by(MenuItem.id)
    return jsonify([as_dict(i, *MENU_FIELDS) for i in rows])


@app.post("/api/restaurants/<int:restaurant_id>/menu")
def create_menu_item(restaurant_id):
    db.get_or_404(Restaurant, restaurant_id)
    data = body()
    item = save(MenuItem(
        restaurant_id=restaurant_id,
        name=text_field(data, "name", "El nombre del plato", 120),
        description=text_field(data, "description", "La descripción", 300, required=False),
        price=price_field(data),
    ))
    return jsonify(as_dict(item, *MENU_FIELDS)), 201


# --- API: reservas ---------------------------------------------------------------------
def reservation_json(reservation, table, customer):
    return {
        "id": reservation.id,
        "date": reservation.date.isoformat(),
        "time": reservation.time.strftime("%H:%M"),
        "table_id": table.id,
        "table": table.name,
        "capacity": table.capacity,
        "customer": customer.name,
    }


@app.get("/api/restaurants/<int:restaurant_id>/reservations")
def list_reservations(restaurant_id):
    """Reservas del restaurante en una fecha (?date=AAAA-MM-DD) y, opcionalmente, a una hora (?time=HH:MM)."""
    db.get_or_404(Restaurant, restaurant_id)
    day = parse_date(request.args.get("date"))
    query = (
        db.session.query(Reservation, RestaurantTable, Customer)
        .join(RestaurantTable, Reservation.table_id == RestaurantTable.id)
        .join(Customer, Reservation.customer_id == Customer.id)
        .filter(RestaurantTable.restaurant_id == restaurant_id, Reservation.date == day)
    )
    if request.args.get("time"):
        query = query.filter(Reservation.time == parse_time(request.args["time"]))
    rows = query.order_by(Reservation.time, RestaurantTable.id).all()
    return jsonify([reservation_json(*row) for row in rows])


@app.post("/api/reservations")
def create_reservation():
    data = body()
    customer = db.session.get(Customer, int_field(data, "customer_id", "El cliente", 1, 2**31 - 1))
    table = db.session.get(RestaurantTable, int_field(data, "table_id", "La mesa", 1, 2**31 - 1))
    if customer is None or table is None:
        raise ApiError("No se encontró el cliente o la mesa.", 404)

    day = parse_date(data.get("date"))
    hour = parse_time(data.get("time"))
    taken = "Esa mesa ya está reservada a esa hora. Elige otra mesa u otra hora."

    if Reservation.query.filter_by(table_id=table.id, date=day, time=hour).first():
        raise ApiError(taken, 409)
    try:
        reservation = save(Reservation(table_id=table.id, customer_id=customer.id, date=day, time=hour))
    except IntegrityError:  # otra persona la reservó justo a la vez
        db.session.rollback()
        raise ApiError(taken, 409)
    return jsonify(reservation_json(reservation, table, customer)), 201


if __name__ == "__main__":
    app.run(debug=True)
