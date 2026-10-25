"""Reglas de negocio de las mesas.

Una mesa está ocupada mientras tenga comandas abiertas (sin cobrar y no canceladas). Al cobrar la
factura esas comandas pasan a pagadas y la mesa vuelve a estar libre. El estado no se guarda en
la tabla: se calcula, así nunca puede quedar desincronizado.
"""
from ..billing.service import pending_bill
from ..core.errors import ApiError
from ..core.extensions import db
from ..core.validation import int_field, text_field
from ..orders.models import Order, open_order_conditions
from ..reservations.models import Reservation
from .models import RestaurantTable


def occupied_table_ids(restaurant_id):
    rows = (
        db.session.query(Order.table_id)
        .filter(Order.restaurant_id == restaurant_id, Order.table_id.isnot(None), *open_order_conditions())
        .distinct()
    )
    return {row[0] for row in rows}


def is_occupied(table_id):
    return (
        db.session.query(Order.id).filter(Order.table_id == table_id, *open_order_conditions()).first()
        is not None
    )


def table_json(table, occupied):
    return {
        "id": table.id,
        "restaurant_id": table.restaurant_id,
        "name": table.name,
        "capacity": table.capacity,
        "status": "ocupada" if occupied else "libre",
    }


def table_detail_json(table):
    """Una mesa con su factura pendiente (si la hay) y el número de reservas que tiene."""
    data = table_json(table, is_occupied(table.id))
    bill = pending_bill(table.id)
    data["pending_bill"] = {"id": bill.id, "total": float(bill.total)} if bill else None
    data["reservations"] = Reservation.query.filter_by(table_id=table.id).count()
    return data


def create_table(restaurant, data):
    table = RestaurantTable(
        restaurant_id=restaurant.id,
        name=text_field(data, "name", "El nombre de la mesa", 40),
        capacity=int_field(data, "capacity", "La capacidad", 1, 50),
    )
    db.session.add(table)
    db.session.commit()
    return table


def update_table(table, data):
    if "name" in data:
        table.name = text_field(data, "name", "El nombre de la mesa", 40)
    if "capacity" in data:
        table.capacity = int_field(data, "capacity", "La capacidad", 1, 50)
    db.session.commit()
    return table


def delete_table(table):
    """Una mesa ocupada no se puede borrar. Sus reservas se borran con ella; las comandas y
    facturas ya cobradas se conservan como historial."""
    if is_occupied(table.id):
        raise ApiError(
            "La mesa está ocupada: tiene comandas sin cobrar. Cóbralas o bórralas antes de borrar la mesa.", 409
        )
    # Comandas canceladas sin cobrar: no tienen sentido sin su mesa
    Order.query.filter(Order.table_id == table.id, Order.is_paid.is_(False)).delete(synchronize_session=False)
    db.session.delete(table)
    db.session.commit()
