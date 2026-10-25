from ..core.extensions import db


class Item(db.Model):
    """Plato o bebida del menú de un restaurante."""

    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(300))
    price = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False)
