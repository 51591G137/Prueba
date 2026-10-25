from ..core.extensions import db


class Reservation(db.Model):
    """Una mesa reservada por un cliente en una franja (fecha y hora)."""

    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = db.Column(
        db.Integer, db.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)

    # La propia base de datos impide reservar dos veces la misma mesa a la misma hora.
    __table_args__ = (db.UniqueConstraint("table_id", "date", "time", name="uq_reservations_slot"),)
