"""Reglas de negocio de las facturas.

Una mesa tiene como mucho UNA factura pendiente de cobro. Mientras exista, no se pueden añadir
comandas a la mesa ni modificar las que ya están en la factura (hay que cobrarla o anularla).
"""
from decimal import Decimal

from ..core.errors import ApiError
from ..core.extensions import db
from ..core.utils import iso_utc, line_total, money, utcnow
from ..core.validation import id_field
from ..orders.models import CANCELLED, Order, OrderItem
from ..payments.models import PaymentMethod
from ..users.service import acting_user
from .models import Bill


def pending_bill(table_id):
    return Bill.query.filter(Bill.table_id == table_id, Bill.close_datetime.is_(None)).first()


def billable_orders(table_id):
    """Comandas de la mesa que aún no están en ninguna factura."""
    return (
        Order.query.filter(
            Order.table_id == table_id,
            Order.bill_id.is_(None),
            Order.is_paid.is_(False),
            Order.status != CANCELLED,
        )
        .order_by(Order.id)
        .all()
    )


def bill_lines(bill):
    """Todos los platos de todas las comandas de la factura, sumando los repetidos."""
    merged = {}
    rows = (
        OrderItem.query.join(Order, OrderItem.order_id == Order.id)
        .filter(Order.bill_id == bill.id)
        .order_by(OrderItem.id)
    )
    for line in rows:
        key = (line.item_name, money(line.unit_price))
        merged[key] = merged.get(key, 0) + line.quantity
    return [
        {
            "name": name,
            "unit_price": float(price),
            "quantity": quantity,
            "subtotal": float(line_total(price, quantity)),
        }
        for (name, price), quantity in merged.items()
    ]


def bill_json(bill, method_names=None, with_lines=False):
    method = None
    if bill.payment_method_id is not None:
        if method_names is not None:
            method = method_names.get(bill.payment_method_id)
        else:
            found = db.session.get(PaymentMethod, bill.payment_method_id)
            method = found.name if found else None
    data = {
        "id": bill.id,
        "restaurant_id": bill.restaurant_id,
        "table_id": bill.table_id,
        "table": bill.table_name,
        "user_id": bill.user_id,
        "status": "pendiente" if bill.close_datetime is None else "pagada",
        "open_datetime": iso_utc(bill.open_datetime),
        "close_datetime": iso_utc(bill.close_datetime),
        "total": float(bill.total),
        "payment_method_id": bill.payment_method_id,
        "payment_method": method,
    }
    if with_lines:
        data["lines"] = bill_lines(bill)
    return data


def restaurant_bills(restaurant_id, limit=100):
    bills = (
        Bill.query.filter_by(restaurant_id=restaurant_id)
        .order_by(Bill.open_datetime.desc(), Bill.id.desc())
        .limit(limit)
        .all()
    )
    names = {m.id: m.name for m in PaymentMethod.query.filter_by(restaurant_id=restaurant_id)}
    return [bill_json(bill, method_names=names) for bill in bills]


def issue_bill(table, data):
    """Emite la factura de la mesa con todas sus comandas sin facturar."""
    user = acting_user(data)
    if pending_bill(table.id):
        raise ApiError("Esta mesa ya tiene una factura pendiente de cobro.", 409)
    orders = billable_orders(table.id)
    if not orders:
        raise ApiError("No hay comandas que facturar en esta mesa.", 409)

    total = sum(
        (line_total(line.unit_price, line.quantity) for order in orders for line in order.lines),
        Decimal("0"),
    )
    bill = Bill(restaurant_id=table.restaurant_id, table_id=table.id, table_name=table.name, user_id=user.id, total=total)
    db.session.add(bill)
    db.session.flush()
    for order in orders:
        order.bill_id = bill.id
    db.session.commit()
    return bill


def pay_bill(bill, data):
    """Cobra la factura con un método de pago. Sus comandas pasan a pagadas y la mesa queda libre."""
    if bill.close_datetime is not None:
        raise ApiError("Esta factura ya está cobrada.", 409)
    method = db.session.get(PaymentMethod, id_field(data, "payment_method_id", "El método de pago"))
    if method is None or method.restaurant_id != bill.restaurant_id:
        raise ApiError("El método de pago no existe en este restaurante.", 404)
    bill.payment_method_id = method.id
    bill.close_datetime = utcnow()
    for order in Order.query.filter_by(bill_id=bill.id):
        order.is_paid = True
    db.session.commit()
    return bill


def void_bill(bill):
    """Anula una factura pendiente: sus comandas vuelven a estar abiertas y se pueden modificar."""
    if bill.close_datetime is not None:
        raise ApiError("Una factura cobrada no se puede anular.", 409)
    for order in Order.query.filter_by(bill_id=bill.id):
        order.bill_id = None
    db.session.flush()
    db.session.delete(bill)
    db.session.commit()
