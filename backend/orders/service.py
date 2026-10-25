"""Reglas de negocio de las comandas.

Una comanda se puede modificar o borrar mientras no esté en una factura. Una comanda cancelada
ya no se puede modificar (solo borrar). Los platos guardan una copia del nombre y del precio.
"""
from decimal import Decimal

from ..billing.service import pending_bill
from ..core.errors import ApiError
from ..core.extensions import db
from ..core.utils import iso_utc, line_total
from ..core.validation import MAX_ID, choice_field, id_field, int_field, text_field
from ..menu.models import Item
from ..users.service import acting_user
from .models import CANCELLED, ORDER_STATUSES, Order, OrderItem

MAX_QUANTITY = 99
MAX_LINES = 50


def order_json(order):
    lines = [
        {
            "id": line.id,
            "item_id": line.item_id,
            "name": line.item_name,
            "unit_price": float(line.unit_price),
            "quantity": line.quantity,
            "subtotal": float(line_total(line.unit_price, line.quantity)),
        }
        for line in order.lines
    ]
    total = sum((line_total(line.unit_price, line.quantity) for line in order.lines), Decimal("0"))
    return {
        "id": order.id,
        "restaurant_id": order.restaurant_id,
        "table_id": order.table_id,
        "user_id": order.user_id,
        "bill_id": order.bill_id,
        "created_at": iso_utc(order.created_at),
        "requests": order.requests,
        "status": order.status,
        "is_paid": order.is_paid,
        "lines": lines,
        "total": float(total),
    }


def table_orders(table_id):
    """Comandas de la mesa que todavía no se han cobrado."""
    return Order.query.filter_by(table_id=table_id, is_paid=False).order_by(Order.id).all()


def parse_items(data, restaurant_id):
    """Lee data['items'] = [{item_id, quantity}, ...]; suma los repetidos y comprueba que son del restaurante."""
    raw = data.get("items")
    if not isinstance(raw, list) or not raw:
        raise ApiError("La comanda necesita al menos un plato.")
    if len(raw) > MAX_LINES:
        raise ApiError(f"Una comanda no puede tener más de {MAX_LINES} platos distintos.")
    wanted = {}
    for entry in raw:
        if not isinstance(entry, dict):
            raise ApiError("El formato de los platos no es válido.")
        item_id = id_field(entry, "item_id", "El plato")
        quantity = int_field(entry, "quantity", "La cantidad", 1, MAX_QUANTITY)
        wanted[item_id] = wanted.get(item_id, 0) + quantity
        if wanted[item_id] > MAX_QUANTITY:
            raise ApiError(f"La cantidad máxima de cada plato es {MAX_QUANTITY}.")
    items = {i.id: i for i in Item.query.filter(Item.id.in_(list(wanted)), Item.restaurant_id == restaurant_id)}
    if len(items) != len(wanted):
        raise ApiError("Algún plato ya no existe en el menú de este restaurante.", 404)
    return wanted, items


def new_line(item, quantity, user_id):
    return OrderItem(
        item_id=item.id, user_id=user_id, item_name=item.name, unit_price=item.price, quantity=quantity
    )


def create_order(table, data):
    user = acting_user(data)
    if pending_bill(table.id):
        raise ApiError(
            "La mesa tiene una factura pendiente de cobro. Cóbrala o anúlala antes de añadir más comandas.", 409
        )
    wanted, items = parse_items(data, table.restaurant_id)
    order = Order(
        restaurant_id=table.restaurant_id,
        table_id=table.id,
        user_id=user.id,
        requests=text_field(data, "requests", "Las notas", 300, required=False),
    )
    for item_id, quantity in wanted.items():
        order.lines.append(new_line(items[item_id], quantity, user.id))
    db.session.add(order)
    db.session.commit()
    return order


def update_order(order, data):
    """Cambia las notas, los platos (se sustituyen por la lista recibida) y/o el estado."""
    if order.bill_id is not None:
        raise ApiError("La comanda ya está en una factura. Anula la factura para poder modificarla.", 409)
    if order.status == CANCELLED:
        raise ApiError("La comanda está cancelada: ya solo se puede borrar.", 409)

    if "requests" in data:
        order.requests = text_field(data, "requests", "Las notas", 300, required=False)

    if "items" in data:
        wanted, items = parse_items(data, order.restaurant_id)
        user_id = acting_user(data).id if "user_id" in data else order.user_id
        existing = {line.item_id: line for line in order.lines}
        for line in list(order.lines):
            if line.item_id in wanted:
                line.quantity = wanted[line.item_id]  # se conserva el precio con el que se pidió
            else:
                order.lines.remove(line)
        for item_id, quantity in wanted.items():
            if item_id not in existing:
                order.lines.append(new_line(items[item_id], quantity, user_id))

    if "status" in data:
        order.status = choice_field(data, "status", "El estado", ORDER_STATUSES)

    db.session.commit()
    return order


def delete_order(order):
    if order.bill_id is not None:
        raise ApiError("La comanda ya está en una factura. Anula la factura para poder borrarla.", 409)
    db.session.delete(order)
    db.session.commit()
