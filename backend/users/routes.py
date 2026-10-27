from flask import Blueprint, jsonify, request, session

from ..core.auth import create_access_token, get_auth_user
from ..core.extensions import db
from ..core.validation import body, text_field
from . import service
from .models import User

bp = Blueprint("users", __name__)


@bp.post("/api/auth/login")
def login():
    data = body()
    username = text_field(data, "username", "El usuario", 80)
    password = text_field(data, "password", "La contraseña", 128, required=False) or ""
    user = service.authenticate_user(username, password)
    session["user_id"] = user.id
    token = create_access_token(user.id)
    return jsonify(token=token, user=service.user_json(user))


@bp.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@bp.get("/api/auth/me")
def me():
    user = get_auth_user()
    if not user:
        return jsonify(error="No autenticado"), 401
    return jsonify(service.user_json(user))


@bp.post("/api/auth/forgot-password")
def forgot_password():
    data = body()
    email = text_field(data, "email", "El correo electrónico", 120)
    res = service.request_password_reset(email, request.host_url)
    return jsonify(ok=True, message="Si el correo está registrado, recibirás un enlace.", token=res.get("token"))


@bp.post("/api/auth/reset-password")
def reset_password():
    data = body()
    token = text_field(data, "token", "El token", 500)
    new_password = text_field(data, "password", "La nueva contraseña", 128)
    service.reset_password_with_token(token, new_password)
    return jsonify(ok=True, message="Contraseña restablecida con éxito.")


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
