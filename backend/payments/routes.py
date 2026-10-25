from flask import Blueprint, jsonify

from ..core.extensions import db
from ..core.validation import body
from ..restaurants.models import Restaurant
from . import service
from .models import PaymentMethod

bp = Blueprint("payments", __name__)


@bp.get("/api/restaurants/<int:restaurant_id>/payment-methods")
def list_methods(restaurant_id):
    db.get_or_404(Restaurant, restaurant_id)
    rows = PaymentMethod.query.filter_by(restaurant_id=restaurant_id).order_by(PaymentMethod.id)
    return jsonify([service.method_json(method) for method in rows])


@bp.post("/api/restaurants/<int:restaurant_id>/payment-methods")
def create_method(restaurant_id):
    restaurant = db.get_or_404(Restaurant, restaurant_id)
    return jsonify(service.method_json(service.create_method(restaurant, body()))), 201
