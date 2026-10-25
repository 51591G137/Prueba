from ..core.extensions import db
from ..core.utils import utcnow

ORDER_STATUSES = ("pedido", "en_preparacion", "listo_para_servir", "servido", "cancelado")
CANCELLED = "cancelado"


class Order(db.Model):
    """Una comanda: lo que se pide para una mesa en un momento dado."""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Si se borra la mesa o el usuario, la comanda (ya cobrada) se conserva como historial.
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id", ondelete="SET NULL"), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    bill_id = db.Column(db.Integer, db.ForeignKey("bills.id", ondelete="SET NULL"), index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    requests = db.Column(db.String(300))
    status = db.Column(db.String(20), nullable=False, default="pedido")
    is_paid = db.Column(db.Boolean, nullable=False, default=False)

    lines = db.relationship(
        "OrderItem",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="OrderItem.id",
        lazy="selectin",
    )


class OrderItem(db.Model):
    """Una línea de la comanda: un plato y cuántos."""

    __tablename__ = "orders_item"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id", ondelete="SET NULL"), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    # Copia del nombre y del precio en el momento de pedir: si luego cambia el menú,
    # las comandas y facturas antiguas se quedan como estaban.
    item_name = db.Column(db.String(120), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)


def open_order_conditions():
    """Una comanda está 'abierta' mientras no se cobre y no esté cancelada.
    Una mesa con comandas abiertas está ocupada."""
    return (Order.is_paid.is_(False), Order.status != CANCELLED)
