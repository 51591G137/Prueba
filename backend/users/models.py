from ..core.extensions import db


class User(db.Model):
    """Persona que gestiona restaurantes (el login se añadirá más adelante)."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)


class UserRestaurant(db.Model):
    """Qué usuarios gestionan qué restaurantes (relación de muchos a muchos)."""

    __tablename__ = "users_restaurants"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    restaurant_id = db.Column(
        db.Integer, db.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (db.UniqueConstraint("user_id", "restaurant_id", name="uq_users_restaurants_pair"),)
