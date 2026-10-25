"""Páginas HTML (las dos apps) y comprobación de estado."""
from flask import Blueprint, current_app, jsonify, send_from_directory

bp = Blueprint("pages", __name__)


def _page(name):
    return send_from_directory(current_app.static_folder, name)


@bp.get("/")
def home():
    return _page("index.html")


@bp.get("/restaurante/")
def restaurant_app():
    return _page("restaurante.html")


@bp.get("/cliente/")
def customer_app():
    return _page("cliente.html")


@bp.get("/health")
def health():
    return jsonify(status="ok")
