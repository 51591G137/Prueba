from flask import Blueprint, jsonify, request

from ..core.extensions import db
from ..core.validation import body, parse_date, parse_time
from ..reservations.service import reserved_table_ids
from ..restaurants.models import Restaurant
from . import service
from .models import RestaurantTable

bp = Blueprint("tables", __name__)


@bp.get("/api/restaurants/<int:restaurant_id>/tables")
def list_tables(restaurant_id):
    """Mesas del restaurante, cada una 'libre' u 'ocupada'.
    Con ?date=AAAA-MM-DD&time=HH:MM cada mesa indica también si está reservada en esa franja
    (?exclude_reservation=ID ignora una reserva concreta, para poder editarla)."""
    db.get_or_404(Restaurant, restaurant_id)
    tables = RestaurantTable.query.filter_by(restaurant_id=restaurant_id).order_by(RestaurantTable.id).all()
    occupied = service.occupied_table_ids(restaurant_id)
    result = [service.table_json(table, table.id in occupied) for table in tables]

    if request.args.get("date") and request.args.get("time"):
        reserved = reserved_table_ids(
            [table.id for table in tables],
            parse_date(request.args["date"]),
            parse_time(request.args["time"]),
            exclude_id=request.args.get("exclude_reservation", type=int),
        )
        for table in result:
            table["reserved"] = table["id"] in reserved
    return jsonify(result)


@bp.post("/api/restaurants/<int:restaurant_id>/tables")
def create_table(restaurant_id):
    restaurant = db.get_or_404(Restaurant, restaurant_id)
    table = service.create_table(restaurant, body())
    return jsonify(service.table_json(table, False)), 201


@bp.get("/api/tables/<int:table_id>")
def get_table(table_id):
    return jsonify(service.table_detail_json(db.get_or_404(RestaurantTable, table_id)))


@bp.patch("/api/tables/<int:table_id>")
def update_table(table_id):
    table = service.update_table(db.get_or_404(RestaurantTable, table_id), body())
    return jsonify(service.table_detail_json(table))


@bp.delete("/api/tables/<int:table_id>")
def delete_table(table_id):
    service.delete_table(db.get_or_404(RestaurantTable, table_id))
    return jsonify(deleted=True)
