"""Reglas de negocio de las reservas."""
from sqlalchemy.exc import IntegrityError

from ..core.errors import ApiError
from ..core.extensions import db
from ..core.validation import id_field, parse_date, parse_time
from ..customers.models import Customer
from ..restaurants.models import Restaurant
from ..tables.models import RestaurantTable
from .models import Reservation

TAKEN = "Esa mesa ya está reservada a esa hora. Elige otra mesa u otra hora."


def reserved_table_ids(table_ids, day, hour, exclude_id=None):
    """Mesas (de entre table_ids) ya reservadas en esa franja. exclude_id ignora una reserva (al editarla)."""
    if not table_ids:
        return set()
    query = Reservation.query.filter(
        Reservation.table_id.in_(list(table_ids)), Reservation.date == day, Reservation.time == hour
    )
    if exclude_id is not None:
        query = query.filter(Reservation.id != exclude_id)
    return {reservation.table_id for reservation in query}


def full_query():
    """Reservas con su mesa, su restaurante y su cliente."""
    return (
        db.session.query(Reservation, RestaurantTable, Restaurant, Customer)
        .join(RestaurantTable, Reservation.table_id == RestaurantTable.id)
        .join(Restaurant, RestaurantTable.restaurant_id == Restaurant.id)
        .join(Customer, Reservation.customer_id == Customer.id)
    )


def reservation_json(reservation, table, restaurant, customer):
    return {
        "id": reservation.id,
        "date": reservation.date.isoformat(),
        "time": reservation.time.strftime("%H:%M"),
        "table_id": table.id,
        "table": table.name,
        "capacity": table.capacity,
        "restaurant_id": restaurant.id,
        "restaurant": restaurant.name,
        "customer_id": customer.id,
        "customer": customer.name,
    }


def full_json(reservation_id):
    row = full_query().filter(Reservation.id == reservation_id).first()
    if row is None:
        raise ApiError("No encontrado.", 404)
    return reservation_json(*row)


def customer_reservations(customer_id, from_day=None):
    query = full_query().filter(Reservation.customer_id == customer_id)
    if from_day is not None:
        query = query.filter(Reservation.date >= from_day)
    rows = query.order_by(Reservation.date, Reservation.time, Reservation.id).all()
    return [reservation_json(*row) for row in rows]


def restaurant_reservations(restaurant_id, day, hour=None):
    query = full_query().filter(RestaurantTable.restaurant_id == restaurant_id, Reservation.date == day)
    if hour is not None:
        query = query.filter(Reservation.time == hour)
    rows = query.order_by(Reservation.time, RestaurantTable.id).all()
    return [reservation_json(*row) for row in rows]


def _commit_or_conflict():
    try:
        db.session.commit()
    except IntegrityError:  # otra persona la reservó justo a la vez
        db.session.rollback()
        raise ApiError(TAKEN, 409)


def create_reservation(data):
    customer = db.session.get(Customer, id_field(data, "customer_id", "El cliente"))
    table = db.session.get(RestaurantTable, id_field(data, "table_id", "La mesa"))
    if customer is None or table is None:
        raise ApiError("No se encontró el cliente o la mesa.", 404)
    day = parse_date(data.get("date"))
    hour = parse_time(data.get("time"))
    if reserved_table_ids([table.id], day, hour):
        raise ApiError(TAKEN, 409)
    reservation = Reservation(table_id=table.id, customer_id=customer.id, date=day, time=hour)
    db.session.add(reservation)
    _commit_or_conflict()
    return reservation


def update_reservation(reservation, data):
    """Cambia la fecha, la hora y/o la mesa (que debe ser del mismo restaurante)."""
    table = db.session.get(RestaurantTable, reservation.table_id)
    if "table_id" in data:
        new_table = db.session.get(RestaurantTable, id_field(data, "table_id", "La mesa"))
        if new_table is None or new_table.restaurant_id != table.restaurant_id:
            raise ApiError("La mesa no existe en este restaurante.", 404)
        table = new_table
    day = parse_date(data["date"]) if "date" in data else reservation.date
    hour = parse_time(data["time"]) if "time" in data else reservation.time
    if reserved_table_ids([table.id], day, hour, exclude_id=reservation.id):
        raise ApiError(TAKEN, 409)
    reservation.table_id, reservation.date, reservation.time = table.id, day, hour
    _commit_or_conflict()
    return reservation


def delete_reservation(reservation):
    db.session.delete(reservation)
    db.session.commit()
