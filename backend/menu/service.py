"""Reglas de negocio del menú."""
from ..core.errors import ApiError
from ..core.extensions import db
from ..core.validation import price_field, text_field
from ..orders.models import Order, OrderItem, open_order_conditions
from .models import Item


def item_json(item):
    return {
        "id": item.id,
        "restaurant_id": item.restaurant_id,
        "name": item.name,
        "description": item.description,
        "price": float(item.price),
    }


def create_item(restaurant, data):
    item = Item(
        restaurant_id=restaurant.id,
        name=text_field(data, "name", "El nombre del plato", 120),
        description=text_field(data, "description", "La descripción", 300, required=False),
        price=price_field(data),
    )
    db.session.add(item)
    db.session.commit()
    return item


def update_item(item, data):
    """Cambiar el precio no afecta a las comandas ya hechas: guardan el precio de cuando se pidieron."""
    if "name" in data:
        item.name = text_field(data, "name", "El nombre del plato", 120)
    if "description" in data:
        item.description = text_field(data, "description", "La descripción", 300, required=False)
    if "price" in data:
        item.price = price_field(data)
    db.session.commit()
    return item


def delete_item(item):
    open_orders = (
        Order.query.join(OrderItem, OrderItem.order_id == Order.id)
        .filter(OrderItem.item_id == item.id, *open_order_conditions())
        .count()
    )
    if open_orders:
        raise ApiError(
            f"Este plato está en {open_orders} comanda(s) sin cobrar. Cóbralas o bórralas antes de quitarlo del menú.",
            409,
        )
    db.session.delete(item)  # las comandas ya cobradas conservan el nombre y el precio
    db.session.commit()
