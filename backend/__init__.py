"""Mi Restaurante: backend Flask organizado en módulos.

Cada carpeta es un módulo con sus tres piezas:
  models.py   tablas de la base de datos
  service.py  reglas de negocio (lo que se puede y no se puede hacer)
  routes.py   direcciones de la API (traducen HTTP a llamadas al servicio)
La carpeta core/ tiene lo común: base de datos, errores y validación.
"""
import os

from flask import Flask
from flask_migrate import upgrade

from .core.config import database_url, normalize_url
from .core.errors import register_error_handlers
from .core.extensions import db, migrate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATIONS_DIR = os.path.join(ROOT, "migrations")


def create_app(overrides=None):
    """Crea la aplicación. 'overrides' (DATABASE_URL, AUTO_MIGRATE) sirve para las pruebas."""
    overrides = overrides or {}
    app = Flask(__name__, static_folder=os.path.join(ROOT, "static"), static_url_path="/static")
    app.config["SQLALCHEMY_DATABASE_URI"] = normalize_url(overrides["DATABASE_URL"]) if overrides.get("DATABASE_URL") else database_url(ROOT)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

    db.init_app(app)
    migrate.init_app(app, db, directory=MIGRATIONS_DIR, render_as_batch=True)

    from . import models  # noqa: F401  (registra las tablas)
    from .routes import register_blueprints

    register_error_handlers(app)
    register_blueprints(app)

    # Al arrancar se aplican las migraciones pendientes (ver migrations/versions/).
    # AUTO_MIGRATE=0 lo desactiva.
    if overrides.get("AUTO_MIGRATE", os.environ.get("AUTO_MIGRATE", "1") != "0"):
        with app.app_context():
            upgrade(directory=MIGRATIONS_DIR)
    return app
