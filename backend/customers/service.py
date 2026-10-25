from ..core.extensions import db
from ..core.validation import text_field
from .models import Customer


def customer_json(customer):
    return {"id": customer.id, "name": customer.name}


def create_customer(data):
    customer = Customer(name=text_field(data, "name", "El nombre", 80))
    db.session.add(customer)
    db.session.commit()
    return customer
