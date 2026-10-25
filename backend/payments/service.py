"""Reglas de negocio de los métodos de pago."""
from ..core.errors import ApiError
from ..core.extensions import db
from ..core.validation import text_field
from .models import PaymentMethod


def method_json(method):
    return {"id": method.id, "restaurant_id": method.restaurant_id, "name": method.name}


def create_method(restaurant, data):
    name = text_field(data, "name", "El nombre del método de pago", 60)
    existing = PaymentMethod.query.filter_by(restaurant_id=restaurant.id).all()
    if any(method.name.casefold() == name.casefold() for method in existing):
        raise ApiError("Ya existe un método de pago con ese nombre.", 409)
    method = PaymentMethod(restaurant_id=restaurant.id, name=name)
    db.session.add(method)
    db.session.commit()
    return method
