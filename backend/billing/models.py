from ..core.extensions import db
from ..core.utils import utcnow


class Bill(db.Model):
    """Factura de una mesa: agrupa todas sus comandas sin facturar.

    Pendiente de cobro mientras close_datetime esté vacío; pagada cuando tiene método de pago.
    """

    __tablename__ = "bills"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id", ondelete="SET NULL"), index=True)
    table_name = db.Column(db.String(40), nullable=False)  # copia: la factura sigue legible si se borra la mesa
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    open_datetime = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    close_datetime = db.Column(db.DateTime(timezone=True))
    total = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False)
    payment_method_id = db.Column(db.Integer, db.ForeignKey("payment_methods.id", ondelete="SET NULL"))
