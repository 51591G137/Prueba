from flask import Blueprint, jsonify

from ..core.extensions import db
from ..core.validation import body
from ..users.models import User
from . import service
from .models import Restaurant

bp = Blueprint("restaurants", __name__)


@bp.get("/api/users/<int:user_id>/restaurants")
def list_user_restaurants(user_id):
    db.get_or_404(User, user_id)
    return jsonify([service.restaurant_json(r) for r in service.user_restaurants(user_id)])


@bp.post("/api/users/<int:user_id>/restaurants")
def create_restaurant(user_id):
    user = db.get_or_404(User, user_id)
    return jsonify(service.restaurant_json(service.create_restaurant(user, body()))), 201


@bp.get("/api/restaurants")
def list_restaurants():
    """Todos los restaurantes (lo usa la app de clientes)."""
    return jsonify([service.restaurant_json(r) for r in Restaurant.query.order_by(Restaurant.id)])


@bp.get("/api/restaurants/<int:restaurant_id>")
def get_restaurant(restaurant_id):
    return jsonify(service.restaurant_json(db.get_or_404(Restaurant, restaurant_id)))
