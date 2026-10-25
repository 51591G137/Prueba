"""Importa todos los modelos para que SQLAlchemy y las migraciones los conozcan."""
from .billing.models import Bill  # noqa: F401
from .customers.models import Customer  # noqa: F401
from .menu.models import Item  # noqa: F401
from .orders.models import Order, OrderItem  # noqa: F401
from .payments.models import PaymentMethod  # noqa: F401
from .reservations.models import Reservation  # noqa: F401
from .restaurants.models import Restaurant  # noqa: F401
from .tables.models import RestaurantTable  # noqa: F401
from .users.models import User, UserRestaurant  # noqa: F401
