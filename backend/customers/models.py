from ..core.extensions import db


class Customer(db.Model):
    """Persona que reserva mesa (app de clientes)."""

    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=True)
    # ponytail: phone-only customer auth; index + unique
    phone = db.Column(db.String(30), unique=True, index=True, nullable=True)
