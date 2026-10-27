from flask import Blueprint, jsonify

from ..core.extensions import db
from ..core.validation import body
from . import service
from .models import Customer

bp = Blueprint("customers", __name__)


@bp.get("/api/customers")
def list_customers():
    return jsonify([service.customer_json(c) for c in Customer.query.order_by(Customer.id)])


@bp.post("/api/customers")
def create_customer():
    return jsonify(service.customer_json(service.create_customer(body()))), 201


@bp.get("/api/customers/<int:customer_id>")
def get_customer(customer_id):
    return jsonify(service.customer_json(db.get_or_404(Customer, customer_id)))


@bp.get("/api/customers/by-phone/<phone>")
def get_customer_by_phone(phone):
    customer = Customer.query.filter_by(phone=phone.strip()).first_or_404()
    return jsonify(service.customer_json(customer))
