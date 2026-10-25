"""Reglas de negocio de los restaurantes."""
from ..core.extensions import db
from ..core.validation import text_field
from ..users.models import UserRestaurant
from .models import Restaurant


def restaurant_json(restaurant):
    return {"id": restaurant.id, "name": restaurant.name, "address": restaurant.address}


def user_restaurants(user_id):
    return (
        Restaurant.query.join(UserRestaurant, UserRestaurant.restaurant_id == Restaurant.id)
        .filter(UserRestaurant.user_id == user_id)
        .order_by(Restaurant.id)
        .all()
    )


def create_restaurant(user, data):
    restaurant = Restaurant(
        name=text_field(data, "name", "El nombre", 120),
        address=text_field(data, "address", "La dirección", 200, required=False),
    )
    db.session.add(restaurant)
    db.session.flush()
    db.session.add(UserRestaurant(user_id=user.id, restaurant_id=restaurant.id))
    db.session.commit()
    return restaurant
