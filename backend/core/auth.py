"""Autenticación y tokens para web y apps móviles (Bearer header + cookies de sesión)."""
from functools import wraps

from flask import current_app, request, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .errors import ApiError
from .extensions import db
from ..users.models import User


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def create_access_token(user_id):
    """Token Bearer para apps móviles o clientes API (válido 30 días)."""
    return _serializer().dumps({"user_id": user_id}, salt="access-token")


def verify_access_token(token, max_age=30 * 86400):
    try:
        data = _serializer().loads(token, salt="access-token", max_age=max_age)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


def create_reset_token(user_id):
    """Token de restablecimiento de contraseña (válido 1 hora)."""
    return _serializer().dumps({"user_id": user_id}, salt="password-reset")


def verify_reset_token(token, max_age=3600):
    """Comprueba el token y devuelve el id de usuario, o None si caducó o es falso."""
    try:
        data = _serializer().loads(token, salt="password-reset", max_age=max_age)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


def get_auth_user():
    """Identifica al usuario vía 'Authorization: Bearer <token>' (móvil) o sesión (web)."""
    # 1) Cabecera Bearer
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        uid = verify_access_token(token)
        if uid:
            return db.session.get(User, uid)
        return None

    # 2) Sesión web
    user_id = session.get("user_id")
    if user_id:
        return db.session.get(User, user_id)
    return None


def current_user():
    return get_auth_user()


def login_required(f):
    """Decorador para proteger rutas de la API del restaurante."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_auth_user():
            raise ApiError("No autenticado. Inicia sesión.", 401)
        return f(*args, **kwargs)
    return decorated
