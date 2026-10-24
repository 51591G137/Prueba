"""
Mi Restaurante - backend (Flask + SQLAlchemy)

  /              página de inicio con enlaces a las dos apps
  /restaurante/  app de gestión: usuarios -> restaurantes -> mesas, menú, reservas,
                 comandas, facturas y métodos de pago
  /cliente/      app de clientes: clientes -> restaurantes -> mesas, menú, reservas
  /api/...       API JSON que usan las dos apps
  /health        comprobación de estado

Sin login ni permisos, a propósito.
"""
import math
import os
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")

# --- Base de datos -----------------------------------------------------------
db_url = os.environ.get("DATABASE_URL", "").strip()
if db_url.startswith("postgres://"):
    db_url = "postgresql://" + db_url[len("postgres://"):]
if not db_url:
    db_url = "sqlite:///" + os.path.join(BASE_DIR, "app.db")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
db = SQLAlchemy(app)


def utcnow():
    """UTC sin tzinfo: se guarda igual en SQLite y en Postgres y no rompe comparaciones."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# --- Modelos -----------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)


class Customer(db.Model):
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
    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id"), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    __table_args__ = (db.UniqueConstraint("table_id", "date", "time", name="uq_reservation_slot"),)


class PaymentMethod(db.Model):
    __tablename__ = "payment_methods"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False, index=True)
    name = db.Column(db.String(60), nullable=False)


class Bill(db.Model):
    __tablename__ = "bills"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False, index=True)
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    paid_at = db.Column(db.DateTime, nullable=True)
    total = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False, default=0)
    payment_method_id = db.Column(db.Integer, db.ForeignKey("payment_methods.id"), nullable=True)


class Order(db.Model):
    """Comanda: cabecera. Los platos van en OrderItem."""
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False, index=True)
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id"), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    status = db.Column(db.String(24), nullable=False, default="pedido")
    requests = db.Column(db.String(300))
    is_paid = db.Column(db.Boolean, nullable=False, default=False)
    items = db.relationship(
        "OrderItem", backref="order", cascade="all, delete-orphan", lazy="selectin"
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("menu_items.id"), nullable=False, index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False)
    requests = db.Column(db.String(200))
    menu_item = db.relationship("MenuItem")


with app.app_context():
    db.create_all()


# --- Utilidades ---------------------------------------------------------------
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
    except (TypeError, ValueError):
        raise ApiError(f"{label} debe ser un número entero.")
    if not minimum <= value <= maximum:
        raise ApiError(f"{label} debe estar entre {minimum} y {maximum}.")
    return value


def price_field(data):
    try:
        value = float(str(data.get("price")).replace(",", ".").strip())
    except (TypeError, ValueError):
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


ORDER_STATUSES = ("pedido", "en_preparacion", "listo_para_servir", "servido", "cancelado")


def status_field(data, default=None):
    value = data.get("status")
    if value is None:
        return default
    if value not in ORDER_STATUSES:
        raise ApiError(
            "Estado no válido. Debe ser uno de: " + ", ".join(ORDER_STATUSES) + "."
        )
    return value


@app.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify(error=err.message), err.status


@app.errorhandler(HTTPException)
def handle_http_error(err):
    if request.path.startswith("/api/"):
        message = "No encontrado." if err.code == 404 else err.description
        return jsonify(error=message), err.code
    return err


# --- Páginas -------------------------------------------------------------------
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


# --- API: usuarios y clientes -------------------------------------------------
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


@app.patch("/api/users/<int:user_id>")
def update_user(user_id):
    user = db.get_or_404(User, user_id)
    data = body()
    if "name" in data:
        user.name = text_field(data, "name", "El nombre", 80)
        db.session.commit()
    return jsonify(as_dict(user, "id", "name"))


@app.delete("/api/users/<int:user_id>")
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    # Si tiene restaurantes, no dejamos borrar en cascada: es demasiado destructivo.
    if Restaurant.query.filter_by(user_id=user.id).count():
        raise ApiError(
            "No se puede borrar un usuario con restaurantes. Bórralos primero.", 409
        )
    db.session.delete(user)
    db.session.commit()
    return "", 204


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


@app.get("/api/customers/<int:customer_id>/reservations")
def list_customer_reservations(customer_id):
    db.get_or_404(Customer, customer_id)
    rows = (
        db.session.query(Reservation, RestaurantTable, Restaurant)
        .join(RestaurantTable, Reservation.table_id == RestaurantTable.id)
        .join(Restaurant, RestaurantTable.restaurant_id == Restaurant.id)
        .filter(Reservation.customer_id == customer_id)
        .order_by(Reservation.date, Reservation.time)
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "date": r.date.isoformat(),
            "time": r.time.strftime("%H:%M"),
            "table_id": t.id,
            "table": t.name,
            "restaurant_id": rest.id,
            "restaurant": rest.name,
        }
        for r, t, rest in rows
    ])


# --- API: restaurantes --------------------------------------------------------
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
    rows = Restaurant.query.order_by(Restaurant.id)
    return jsonify([as_dict(r, *RESTAURANT_FIELDS) for r in rows])


@app.get("/api/restaurants/<int:restaurant_id>")
def get_restaurant(restaurant_id):
    return jsonify(as_dict(db.get_or_404(Restaurant, restaurant_id), *RESTAURANT_FIELDS))


# --- API: mesas --------------------------------------------------------------
@app.get("/api/restaurants/<int:restaurant_id>/tables")
def list_tables(restaurant_id):
    db.get_or_404(Restaurant, restaurant_id)
    tables = (
        RestaurantTable.query.filter_by(restaurant_id=restaurant_id)
        .order_by(RestaurantTable.id)
        .all()
    )
    table_ids = [t.id for t in tables]

    occupied_ids = set()
    if table_ids:
        occupied_ids = {
            row[0]
            for row in db.session.query(Order.table_id)
            .filter(
                Order.table_id.in_(table_ids),
                Order.is_paid.is_(False),
                Order.status != "cancelado",
            )
            .distinct()
            .all()
        }

    result = [
        {
            "id": t.id,
            "name": t.name,
            "capacity": t.capacity,
            "status": "occupied" if t.id in occupied_ids else "free",
        }
        for t in tables
    ]

    if request.args.get("date") and request.args.get("time"):
        day = parse_date(request.args["date"])
        hour = parse_time(request.args["time"])
        taken = {
            r.table_id
            for r in Reservation.query.filter(
                Reservation.table_id.in_(table_ids),
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


@app.patch("/api/restaurants/<int:restaurant_id>/tables/<int:table_id>")
def update_table(restaurant_id, table_id):
    table = db.get_or_404(RestaurantTable, table_id)
    if table.restaurant_id != restaurant_id:
        raise ApiError("La mesa no pertenece a este restaurante.", 404)
    data = body()
    if "name" in data:
        table.name = text_field(data, "name", "El nombre de la mesa", 40)
    if "capacity" in data:
        table.capacity = int_field(data, "capacity", "La capacidad", 1, 50)
    db.session.commit()
    return jsonify(as_dict(table, "id", "name", "capacity"))


@app.delete("/api/restaurants/<int:restaurant_id>/tables/<int:table_id>")
def delete_table(restaurant_id, table_id):
    table = db.get_or_404(RestaurantTable, table_id)
    if table.restaurant_id != restaurant_id:
        raise ApiError("La mesa no pertenece a este restaurante.", 404)

    unpaid = (
        Order.query.filter_by(table_id=table_id, is_paid=False)
        .filter(Order.status != "cancelado")
        .count()
    )
    if unpaid:
        raise ApiError(
            "No se puede borrar la mesa porque tiene comandas pendientes de cobro.", 409
        )

    # Al borrar la mesa, arrastramos sus comandas, facturas y reservas ya pagadas
    orders = Order.query.filter_by(table_id=table_id).all()
    bill_ids = {o.bill_id for o in orders if o.bill_id}
    for order in orders:
        db.session.delete(order)
    if bill_ids:
        Bill.query.filter(Bill.id.in_(bill_ids)).delete(synchronize_session=False)
    Reservation.query.filter_by(table_id=table_id).delete(synchronize_session=False)
    db.session.delete(table)
    db.session.commit()
    return "", 204


# --- API: menú ---------------------------------------------------------------
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


@app.patch("/api/restaurants/<int:restaurant_id>/menu/<int:item_id>")
def update_menu_item(restaurant_id, item_id):
    item = db.get_or_404(MenuItem, item_id)
    if item.restaurant_id != restaurant_id:
        raise ApiError("El plato no pertenece a este restaurante.", 404)
    data = body()
    if "name" in data:
        item.name = text_field(data, "name", "El nombre del plato", 120)
    if "description" in data:
        item.description = text_field(data, "description", "La descripción", 300, required=False)
    if "price" in data:
        item.price = price_field(data)
    db.session.commit()
    return jsonify(as_dict(item, *MENU_FIELDS))


@app.delete("/api/restaurants/<int:restaurant_id>/menu/<int:item_id>")
def delete_menu_item(restaurant_id, item_id):
    item = db.get_or_404(MenuItem, item_id)
    if item.restaurant_id != restaurant_id:
        raise ApiError("El plato no pertenece a este restaurante.", 404)
    if OrderItem.query.filter_by(item_id=item.id).count():
        raise ApiError(
            "No se puede borrar un plato que ya está en alguna comanda.", 409
        )
    db.session.delete(item)
    db.session.commit()
    return "", 204


# --- API: métodos de pago ----------------------------------------------------
@app.get("/api/restaurants/<int:restaurant_id>/payment-methods")
def list_payment_methods(restaurant_id):
    db.get_or_404(Restaurant, restaurant_id)
    rows = (
        PaymentMethod.query.filter_by(restaurant_id=restaurant_id)
        .order_by(PaymentMethod.id)
    )
    return jsonify([as_dict(pm, "id", "name") for pm in rows])


@app.post("/api/restaurants/<int:restaurant_id>/payment-methods")
def create_payment_method(restaurant_id):
    db.get_or_404(Restaurant, restaurant_id)
    pm = save(PaymentMethod(
        restaurant_id=restaurant_id,
        name=text_field(body(), "name", "El nombre del método de pago", 60),
    ))
    return jsonify(as_dict(pm, "id", "name")), 201


@app.patch("/api/restaurants/<int:restaurant_id>/payment-methods/<int:pm_id>")
def update_payment_method(restaurant_id, pm_id):
    pm = db.get_or_404(PaymentMethod, pm_id)
    if pm.restaurant_id != restaurant_id:
        raise ApiError("El método de pago no pertenece a este restaurante.", 404)
    data = body()
    if "name" in data:
        pm.name = text_field(data, "name", "El nombre del método de pago", 60)
        db.session.commit()
    return jsonify(as_dict(pm, "id", "name"))


@app.delete("/api/restaurants/<int:restaurant_id>/payment-methods/<int:pm_id>")
def delete_payment_method(restaurant_id, pm_id):
    pm = db.get_or_404(PaymentMethod, pm_id)
    if pm.restaurant_id != restaurant_id:
        raise ApiError("El método de pago no pertenece a este restaurante.", 404)
    if Bill.query.filter_by(payment_method_id=pm.id).count():
        raise ApiError(
            "No se puede borrar un método de pago ya usado en alguna factura.", 409
        )
    db.session.delete(pm)
    db.session.commit()
    return "", 204


# --- API: reservas ------------------------------------------------------------
def reservation_json(reservation, table, customer):
    return {
        "id": reservation.id,
        "date": reservation.date.isoformat(),
        "time": reservation.time.strftime("%H:%M"),
        "table_id": table.id,
        "table": table.name,
        "capacity": table.capacity,
        "customer_id": customer.id,
        "customer": customer.name,
    }


@app.get("/api/restaurants/<int:restaurant_id>/reservations")
def list_reservations(restaurant_id):
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
    taken_msg = "Esa mesa ya está reservada a esa hora. Elige otra mesa u otra hora."

    if Reservation.query.filter_by(table_id=table.id, date=day, time=hour).first():
        raise ApiError(taken_msg, 409)
    try:
        reservation = save(Reservation(
            table_id=table.id, customer_id=customer.id, date=day, time=hour
        ))
    except IntegrityError:
        db.session.rollback()
        raise ApiError(taken_msg, 409)
    return jsonify(reservation_json(reservation, table, customer)), 201


@app.patch("/api/reservations/<int:reservation_id>")
def update_reservation(reservation_id):
    reservation = db.get_or_404(Reservation, reservation_id)
    data = body()
    new_date = parse_date(data["date"]) if "date" in data else reservation.date
    new_time = parse_time(data["time"]) if "time" in data else reservation.time

    clash = Reservation.query.filter(
        Reservation.id != reservation.id,
        Reservation.table_id == reservation.table_id,
        Reservation.date == new_date,
        Reservation.time == new_time,
    ).first()
    if clash:
        raise ApiError("Esa mesa ya está reservada a esa hora.", 409)
    reservation.date = new_date
    reservation.time = new_time
    db.session.commit()
    table = db.session.get(RestaurantTable, reservation.table_id)
    customer = db.session.get(Customer, reservation.customer_id)
    return jsonify(reservation_json(reservation, table, customer))


@app.delete("/api/reservations/<int:reservation_id>")
def delete_reservation(reservation_id):
    reservation = db.get_or_404(Reservation, reservation_id)
    db.session.delete(reservation)
    db.session.commit()
    return "", 204


# --- API: comandas ------------------------------------------------------------
def order_item_json(oi):
    return {
        "id": oi.id,
        "item_id": oi.item_id,
        "name": oi.menu_item.name if oi.menu_item else None,
        "quantity": oi.quantity,
        "price": float(oi.price),
        "subtotal": round(float(oi.price) * oi.quantity, 2),
        "requests": oi.requests,
    }


def order_json(order):
    return {
        "id": order.id,
        "table_id": order.table_id,
        "restaurant_id": order.restaurant_id,
        "customer_id": order.customer_id,
        "user_id": order.user_id,
        "bill_id": order.bill_id,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "status": order.status,
        "requests": order.requests,
        "is_paid": order.is_paid,
        "items": [order_item_json(oi) for oi in order.items],
        "total": round(sum(float(oi.price) * oi.quantity for oi in order.items), 2),
    }


@app.get("/api/restaurants/<int:restaurant_id>/orders")
def list_orders(restaurant_id):
    db.get_or_404(Restaurant, restaurant_id)
    query = Order.query.filter_by(restaurant_id=restaurant_id)
    if request.args.get("table_id"):
        query = query.filter_by(table_id=int_field(request.args, "table_id", "La mesa", 1, 2**31 - 1))
    if request.args.get("active") == "true":
        query = query.filter(Order.is_paid.is_(False), Order.status != "cancelado")
    orders = query.order_by(Order.created_at.desc(), Order.id.desc()).all()
    return jsonify([order_json(o) for o in orders])


@app.get("/api/orders/<int:order_id>")
def get_order(order_id):
    return jsonify(order_json(db.get_or_404(Order, order_id)))


@app.post("/api/restaurants/<int:restaurant_id>/orders")
def create_order(restaurant_id):
    restaurant = db.get_or_404(Restaurant, restaurant_id)
    data = body()

    table = db.session.get(RestaurantTable, int_field(data, "table_id", "La mesa", 1, 2**31 - 1))
    if table is None or table.restaurant_id != restaurant_id:
        raise ApiError("La mesa no pertenece a este restaurante.", 404)

    customer = None
    if data.get("customer_id"):
        customer = db.session.get(
            Customer, int_field(data, "customer_id", "El cliente", 1, 2**31 - 1)
        )
        if customer is None:
            raise ApiError("El cliente no existe.", 404)

    order = Order(
        restaurant_id=restaurant_id,
        table_id=table.id,
        user_id=restaurant.user_id,
        customer_id=customer.id if customer else None,
        requests=text_field(data, "requests", "Las peticiones", 300, required=False),
        status="pedido",
    )
    db.session.add(order)
    db.session.flush()

    items = data.get("items") or []
    if not isinstance(items, list):
        raise ApiError("items debe ser una lista.")

    for item_data in items:
        if not isinstance(item_data, dict):
            continue
        menu_item = db.session.get(
            MenuItem, int_field(item_data, "item_id", "El plato", 1, 2**31 - 1)
        )
        if menu_item is None or menu_item.restaurant_id != restaurant_id:
            raise ApiError(
                "Uno de los platos no existe o no pertenece a este restaurante.", 404
            )
        quantity = int_field(item_data, "quantity", "La cantidad", 1, 99)
        db.session.add(OrderItem(
            order_id=order.id,
            item_id=menu_item.id,
            quantity=quantity,
            price=float(menu_item.price),
            requests=text_field(item_data, "requests", "Las peticiones", 200, required=False),
        ))

    db.session.commit()
    return jsonify(order_json(order)), 201


def _assert_order_editable(order):
    if order.bill_id is not None:
        raise ApiError(
            "Esta comanda ya está facturada y no se puede modificar.", 409
        )


@app.patch("/api/orders/<int:order_id>")
def update_order(order_id):
    order = db.get_or_404(Order, order_id)
    _assert_order_editable(order)
    data = body()
    if "status" in data:
        order.status = status_field(data)
    if "requests" in data:
        order.requests = text_field(data, "requests", "Las peticiones", 300, required=False)
    db.session.commit()
    return jsonify(order_json(order))


@app.delete("/api/orders/<int:order_id>")
def delete_order(order_id):
    order = db.get_or_404(Order, order_id)
    _assert_order_editable(order)
    db.session.delete(order)
    db.session.commit()
    return "", 204


@app.post("/api/orders/<int:order_id>/items")
def add_order_item(order_id):
    order = db.get_or_404(Order, order_id)
    _assert_order_editable(order)
    data = body()
    menu_item = db.session.get(
        MenuItem, int_field(data, "item_id", "El plato", 1, 2**31 - 1)
    )
    if menu_item is None or menu_item.restaurant_id != order.restaurant_id:
        raise ApiError("El plato no existe o no pertenece a este restaurante.", 404)
    item = OrderItem(
        order_id=order.id,
        item_id=menu_item.id,
        quantity=int_field(data, "quantity", "La cantidad", 1, 99),
        price=float(menu_item.price),
        requests=text_field(data, "requests", "Las peticiones", 200, required=False),
    )
    db.session.add(item)
    db.session.commit()
    db.session.refresh(order)
    return jsonify(order_json(order)), 201


@app.patch("/api/orders/<int:order_id>/items/<int:item_id>")
def update_order_item(order_id, item_id):
    order = db.get_or_404(Order, order_id)
    _assert_order_editable(order)
    oi = db.get_or_404(OrderItem, item_id)
    if oi.order_id != order.id:
        raise ApiError("El plato no pertenece a esta comanda.", 404)
    data = body()
    if "quantity" in data:
        oi.quantity = int_field(data, "quantity", "La cantidad", 1, 99)
    if "requests" in data:
        oi.requests = text_field(data, "requests", "Las peticiones", 200, required=False)
    db.session.commit()
    db.session.refresh(order)
    return jsonify(order_json(order))


@app.delete("/api/orders/<int:order_id>/items/<int:item_id>")
def delete_order_item(order_id, item_id):
    order = db.get_or_404(Order, order_id)
    _assert_order_editable(order)
    oi = db.get_or_404(OrderItem, item_id)
    if oi.order_id != order.id:
        raise ApiError("El plato no pertenece a esta comanda.", 404)
    db.session.delete(oi)
    db.session.commit()
    db.session.refresh(order)
    return jsonify(order_json(order))


# --- API: facturas ------------------------------------------------------------
def bill_json(bill):
    return {
        "id": bill.id,
        "restaurant_id": bill.restaurant_id,
        "table_id": bill.table_id,
        "customer_id": bill.customer_id,
        "user_id": bill.user_id,
        "created_at": bill.created_at.isoformat() if bill.created_at else None,
        "paid_at": bill.paid_at.isoformat() if bill.paid_at else None,
        "total": float(bill.total),
        "payment_method_id": bill.payment_method_id,
    }


def _bill_for_table(table, orders, payment_method, customer_id):
    total = round(sum(float(oi.price) * oi.quantity for o in orders for oi in o.items), 2)
    if total <= 0:
        raise ApiError("Las comandas no tienen importe.")
    now = utcnow()
    bill = Bill(
        restaurant_id=table.restaurant_id,
        table_id=table.id,
        user_id=None,
        customer_id=customer_id,
        created_at=now,
        paid_at=now,
        total=total,
        payment_method_id=payment_method.id if payment_method else None,
    )
    db.session.add(bill)
    db.session.flush()
    for order in orders:
        order.bill_id = bill.id
        order.is_paid = payment_method is not None
    return bill


@app.post("/api/tables/<int:table_id>/bill")
def create_bill(table_id):
    table = db.get_or_404(RestaurantTable, table_id)
    data = body()

    orders = (
        Order.query.filter_by(table_id=table_id, is_paid=False, bill_id=None)
        .filter(Order.status != "cancelado")
        .all()
    )
    if not orders:
        raise ApiError("La mesa no tiene comandas pendientes.", 409)

    customer_id = data.get("customer_id") or next(
        (o.customer_id for o in orders if o.customer_id), None
    )
    if customer_id:
        if db.session.get(Customer, int(customer_id)) is None:
            raise ApiError("El cliente no existe.", 404)

    payment_method = None
    if data.get("payment_method_id") is not None:
        pm_id = int_field(data, "payment_method_id", "El método de pago", 1, 2**31 - 1)
        payment_method = db.session.get(PaymentMethod, pm_id)
        if payment_method is None or payment_method.restaurant_id != table.restaurant_id:
            raise ApiError(
                "El método de pago no existe o no pertenece a este restaurante.", 404
            )

    bill = _bill_for_table(table, orders, payment_method, customer_id)
    db.session.commit()
    return jsonify(bill_json(bill)), 201


@app.post("/api/bills/<int:bill_id>/pay")
def pay_bill(bill_id):
    bill = db.get_or_404(Bill, bill_id)
    if bill.paid_at is not None:
        raise ApiError("Esta factura ya está pagada.", 409)
    data = body()
    pm_id = int_field(data, "payment_method_id", "El método de pago", 1, 2**31 - 1)
    pm = db.session.get(PaymentMethod, pm_id)
    if pm is None or pm.restaurant_id != bill.restaurant_id:
        raise ApiError(
            "El método de pago no existe o no pertenece a este restaurante.", 404
        )
    bill.payment_method_id = pm.id
    bill.paid_at = utcnow()
    for order in Order.query.filter_by(bill_id=bill.id).all():
        order.is_paid = True
    db.session.commit()
    return jsonify(bill_json(bill))


@app.get("/api/bills/<int:bill_id>")
def get_bill(bill_id):
    return jsonify(bill_json(db.get_or_404(Bill, bill_id)))


@app.get("/api/restaurants/<int:restaurant_id>/bills")
def list_bills(restaurant_id):
    db.get_or_404(Restaurant, restaurant_id)
    rows = (
        Bill.query.filter_by(restaurant_id=restaurant_id)
        .order_by(Bill.created_at.desc(), Bill.id.desc())
        .all()
    )
    return jsonify([bill_json(b) for b in rows])


if __name__ == "__main__":
    app.run(debug=True)