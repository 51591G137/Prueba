from flask import Blueprint, jsonify

from ..core.extensions import db
from ..core.validation import body
from ..restaurants.models import Restaurant
from . import service
from .models import Item

bp = Blueprint("menu", __name__)


@bp.get("/api/restaurants/<int:restaurant_id>/menu")
def list_menu(restaurant_id):
    db.get_or_404(Restaurant, restaurant_id)
    rows = Item.query.filter_by(restaurant_id=restaurant_id).order_by(Item.id)
    return jsonify([service.item_json(item) for item in rows])


@bp.post("/api/restaurants/<int:restaurant_id>/menu")
def create_item(restaurant_id):
    restaurant = db.get_or_404(Restaurant, restaurant_id)
    return jsonify(service.item_json(service.create_item(restaurant, body()))), 201


@bp.get("/api/menu/<int:item_id>")
def get_item(item_id):
    return jsonify(service.item_json(db.get_or_404(Item, item_id)))


@bp.patch("/api/menu/<int:item_id>")
def update_item(item_id):
    item = service.update_item(db.get_or_404(Item, item_id), body())
    return jsonify(service.item_json(item))


@bp.delete("/api/menu/<int:item_id>")
def delete_item(item_id):
    service.delete_item(db.get_or_404(Item, item_id))
    return jsonify(deleted=True)
