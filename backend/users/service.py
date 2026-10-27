"""Reglas de negocio de los usuarios."""
from flask import session
from sqlalchemy.orm import aliased
from werkzeug.security import check_password_hash, generate_password_hash

from ..core.errors import ApiError
from ..core.extensions import db
from ..core.validation import id_field, text_field
from ..restaurants.models import Restaurant
from .models import User, UserRestaurant


def user_json(user):
    data = {"id": user.id, "username": user.username}
    if user.email:
        data["email"] = user.email
    return data


def acting_user(data):
    """El usuario que hace una acción (comanda, factura...). Llega en Bearer header, sesión o data['user_id']."""
    from ..core.auth import get_auth_user
    auth_user = get_auth_user()
    if auth_user is not None:
        return auth_user
    uid = data.get("user_id") if isinstance(data, dict) else None
    if not uid:
        raise ApiError("El usuario es obligatorio.", 400)
    user = db.session.get(User, id_field({"user_id": uid}, "user_id", "El usuario"))
    if user is None:
        raise ApiError("El usuario no existe.", 404)
    return user


def authenticate_user(username, password):
    """Valida usuario y contraseña."""
    user = User.query.filter_by(username=username).first()
    if not user:
        raise ApiError("Usuario o contraseña incorrectos.", 401)
    if user.password_hash:
        if not password or not check_password_hash(user.password_hash, password):
            raise ApiError("Usuario o contraseña incorrectos.", 401)
    elif password:
        # ponytail: asigna contraseña en el primer inicio para usuarios antiguos sin hash
        user.password_hash = generate_password_hash(password)
        db.session.commit()
    return user


def create_user(data):
    username = text_field(data, "username", "El nombre de usuario", 80)
    existing = User.query.filter_by(username=username).first()
    if existing:
        raise ApiError("Ese nombre de usuario ya está en uso.", 409)
    email = text_field(data, "email", "El correo electrónico", 120, required=False)
    if email:
        email = email.lower()
        if User.query.filter_by(email=email).first():
            raise ApiError("Ese correo electrónico ya está registrado.", 409)
    password = text_field(data, "password", "La contraseña", 128, required=False)
    pwd_hash = generate_password_hash(password) if password else None
    user = User(username=username, email=email, password_hash=pwd_hash)
    db.session.add(user)
    db.session.commit()
    return user


def update_user(user, data):
    if "username" in data:
        new_username = text_field(data, "username", "El nombre de usuario", 80)
        if new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                raise ApiError("Ese nombre de usuario ya está en uso.", 409)
            user.username = new_username
    if "email" in data:
        new_email = text_field(data, "email", "El correo electrónico", 120, required=False)
        if new_email:
            new_email = new_email.lower()
            if new_email != user.email and User.query.filter_by(email=new_email).first():
                raise ApiError("Ese correo electrónico ya está registrado.", 409)
        user.email = new_email
    if "password" in data:
        password = text_field(data, "password", "La contraseña", 128, required=False)
        user.password_hash = generate_password_hash(password) if password else None
    db.session.commit()
    return user


def request_password_reset(email, base_url=""):
    """Genera token de restablecimiento y envía correo."""
    from ..core.auth import create_reset_token
    from ..core.email import send_email

    user = User.query.filter_by(email=email.strip().lower()).first()
    if not user:
        # ponytail: responde igual si no existe para evitar enumeración de correos
        return {"sent": False, "token": None}
    token = create_reset_token(user.id)
    reset_link = f"{base_url.rstrip('/')}/restaurante/#/reset-password?token={token}"
    body = (
        f"Hola {user.username},\n\n"
        f"Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace (válido durante 1 hora):\n\n"
        f"{reset_link}\n\n"
        f"Si no solicitaste este cambio, ignora este correo.\n"
    )
    send_email(user.email, "Restablecer contraseña - Mi Restaurante", body)
    return {"sent": True, "token": token}


def reset_password_with_token(token, new_password):
    """Verifica el token y guarda la nueva contraseña."""
    from ..core.auth import verify_reset_token

    user_id = verify_reset_token(token)
    if not user_id:
        raise ApiError("El enlace de restablecimiento es inválido o ha caducado.", 400)
    user = db.session.get(User, user_id)
    if not user:
        raise ApiError("Usuario no encontrado.", 404)
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return user


def exclusive_restaurants(user):
    """Restaurantes que solo gestiona este usuario: si él desaparece, nadie los gestionaría."""
    other = aliased(UserRestaurant)  # alias: la subconsulta no debe confundirse con la consulta exterior
    has_other_user = (
        db.session.query(other.id).filter(other.restaurant_id == Restaurant.id, other.user_id != user.id).exists()
    )
    return (
        Restaurant.query.join(UserRestaurant, UserRestaurant.restaurant_id == Restaurant.id)
        .filter(UserRestaurant.user_id == user.id, ~has_other_user)
        .order_by(Restaurant.id)
        .all()
    )


def delete_user(user):
    """Borra al usuario y los restaurantes que solo gestionaba él, con todo lo que contienen
    (mesas, menú, comandas, facturas y reservas: lo hace la base de datos en cascada)."""
    restaurants = exclusive_restaurants(user)
    for restaurant in restaurants:
        db.session.delete(restaurant)
    db.session.delete(user)
    db.session.commit()
    return len(restaurants)
