from flask import Blueprint, jsonify, request

from ..core.extensions import db
from ..core.validation import body, parse_date, parse_time
from ..customers.models import Customer
from ..restaurants.models import Restaurant
from . import service
from .models import Reservation

bp = Blueprint("reservations", __name__)


@bp.post("/api/reservations")
def create_reservation():
    reservation = service.create_reservation(body())
    return jsonify(service.full_json(reservation.id)), 201


@bp.get("/api/reservations/<int:reservation_id>")
def get_reservation(reservation_id):
    return jsonify(service.full_json(reservation_id))


@bp.patch("/api/reservations/<int:reservation_id>")
def update_reservation(reservation_id):
    reservation = service.update_reservation(db.get_or_404(Reservation, reservation_id), body())
    return jsonify(service.full_json(reservation.id))


@bp.delete("/api/reservations/<int:reservation_id>")
def delete_reservation(reservation_id):
    service.delete_reservation(db.get_or_404(Reservation, reservation_id))
    return jsonify(deleted=True)


@bp.get("/api/customers/<int:customer_id>/reservations")
def list_customer_reservations(customer_id):
    """Reservas de un cliente. Con ?from=AAAA-MM-DD solo las de esa fecha en adelante."""
    db.get_or_404(Customer, customer_id)
    from_day = parse_date(request.args["from"]) if request.args.get("from") else None
    return jsonify(service.customer_reservations(customer_id, from_day))


@bp.get("/api/restaurants/<int:restaurant_id>/reservations")
def list_restaurant_reservations(restaurant_id):
    """Reservas del restaurante en una fecha (?date=AAAA-MM-DD) y, opcionalmente, a una hora (?time=HH:MM)."""
    db.get_or_404(Restaurant, restaurant_id)
    day = parse_date(request.args.get("date"))
    hour = parse_time(request.args["time"]) if request.args.get("time") else None
    return jsonify(service.restaurant_reservations(restaurant_id, day, hour))
