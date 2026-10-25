from ..core.extensions import db


class PaymentMethod(db.Model):
    """Forma de cobrar de un restaurante: efectivo, tarjeta, bizum..."""

    __tablename__ = "payment_methods"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(60), nullable=False)

    __table_args__ = (db.UniqueConstraint("restaurant_id", "name", name="uq_payment_methods_name"),)
