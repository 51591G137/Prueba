"""Reglas de negocio de los usuarios."""
from sqlalchemy.orm import aliased

from ..core.errors import ApiError
from ..core.extensions import db
from ..core.validation import id_field, text_field
from ..restaurants.models import Restaurant
from .models import User, UserRestaurant


def user_json(user):
    return {"id": user.id, "username": user.username}


def acting_user(data):
    """El usuario que hace una acción (comanda, factura...). Llega en data['user_id']."""
    user = db.session.get(User, id_field(data, "user_id", "El usuario"))
    if user is None:
        raise ApiError("El usuario no existe.", 404)
    return user


def create_user(data):
    user = User(username=text_field(data, "username", "El nombre de usuario", 80))
    db.session.add(user)
    db.session.commit()
    return user


def update_user(user, data):
    if "username" in data:
        user.username = text_field(data, "username", "El nombre de usuario", 80)
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
