from ..core.errors import ApiError
from ..core.extensions import db
from ..core.validation import text_field
from .models import Customer


def customer_json(customer):
    return {"id": customer.id, "name": customer.name or customer.phone, "phone": customer.phone}


def get_or_create_by_phone(phone, name=None):
    # ponytail: find-or-create customer by phone, zero friction
    customer = Customer.query.filter_by(phone=phone).first()
    if customer is None:
        customer = Customer(phone=phone, name=name or phone)
        db.session.add(customer)
        db.session.commit()
    elif name and customer.name in (None, "", customer.phone):
        customer.name = name
        db.session.commit()
    return customer


def create_customer(data):
    phone = text_field(data, "phone", "El teléfono", 30, required=False)
    name = text_field(data, "name", "El nombre", 80, required=False)
    if not phone and not name:
        raise ApiError("Se requiere al menos el teléfono o el nombre.")
    if phone:
        return get_or_create_by_phone(phone, name)
    customer = Customer(name=name)
    db.session.add(customer)
    db.session.commit()
    return customer
