from flask import Blueprint, jsonify

from ..core.extensions import db
from ..core.validation import body
from ..tables.models import RestaurantTable
from . import service
from .models import Order

bp = Blueprint("orders", __name__)


@bp.get("/api/tables/<int:table_id>/orders")
def list_orders(table_id):
    """Comandas de la mesa que aún no se han cobrado."""
    db.get_or_404(RestaurantTable, table_id)
    return jsonify([service.order_json(order) for order in service.table_orders(table_id)])


@bp.post("/api/tables/<int:table_id>/orders")
def create_order(table_id):
    table = db.get_or_404(RestaurantTable, table_id)
    return jsonify(service.order_json(service.create_order(table, body()))), 201


@bp.get("/api/orders/<int:order_id>")
def get_order(order_id):
    return jsonify(service.order_json(db.get_or_404(Order, order_id)))


@bp.patch("/api/orders/<int:order_id>")
def update_order(order_id):
    order = service.update_order(db.get_or_404(Order, order_id), body())
    return jsonify(service.order_json(order))


@bp.delete("/api/orders/<int:order_id>")
def delete_order(order_id):
    service.delete_order(db.get_or_404(Order, order_id))
    return jsonify(deleted=True)
