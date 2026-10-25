from flask import Blueprint, jsonify

from ..core.extensions import db
from ..core.validation import body
from ..restaurants.models import Restaurant
from ..tables.models import RestaurantTable
from . import service
from .models import Bill

bp = Blueprint("billing", __name__)


@bp.get("/api/restaurants/<int:restaurant_id>/bills")
def list_bills(restaurant_id):
    """Facturas del restaurante, de la más reciente a la más antigua."""
    db.get_or_404(Restaurant, restaurant_id)
    return jsonify(service.restaurant_bills(restaurant_id))


@bp.post("/api/tables/<int:table_id>/bills")
def issue_bill(table_id):
    """Emite la factura de la mesa con todas sus comandas sin facturar."""
    table = db.get_or_404(RestaurantTable, table_id)
    bill = service.issue_bill(table, body())
    return jsonify(service.bill_json(bill, with_lines=True)), 201


@bp.get("/api/bills/<int:bill_id>")
def get_bill(bill_id):
    return jsonify(service.bill_json(db.get_or_404(Bill, bill_id), with_lines=True))


@bp.post("/api/bills/<int:bill_id>/pay")
def pay_bill(bill_id):
    bill = service.pay_bill(db.get_or_404(Bill, bill_id), body())
    return jsonify(service.bill_json(bill, with_lines=True))


@bp.delete("/api/bills/<int:bill_id>")
def void_bill(bill_id):
    service.void_bill(db.get_or_404(Bill, bill_id))
    return jsonify(deleted=True)
