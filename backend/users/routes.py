from flask import Blueprint, jsonify

from ..core.extensions import db
from ..core.validation import body
from . import service
from .models import User

bp = Blueprint("users", __name__)


@bp.get("/api/users")
def list_users():
    return jsonify([service.user_json(user) for user in User.query.order_by(User.id)])


@bp.post("/api/users")
def create_user():
    return jsonify(service.user_json(service.create_user(body()))), 201


@bp.get("/api/users/<int:user_id>")
def get_user(user_id):
    return jsonify(service.user_json(db.get_or_404(User, user_id)))


@bp.patch("/api/users/<int:user_id>")
def update_user(user_id):
    user = service.update_user(db.get_or_404(User, user_id), body())
    return jsonify(service.user_json(user))


@bp.delete("/api/users/<int:user_id>")
def delete_user(user_id):
    restaurants_deleted = service.delete_user(db.get_or_404(User, user_id))
    return jsonify(deleted=True, restaurants_deleted=restaurants_deleted)
