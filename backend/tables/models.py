from ..core.extensions import db


class RestaurantTable(db.Model):
    """Una mesa del restaurante (no se llama Table para no chocar con db.Table).

    Si está ocupada o libre no se guarda: se calcula a partir de sus comandas (ver service.py).
    """

    __tablename__ = "tables"

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(db.String(40), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
