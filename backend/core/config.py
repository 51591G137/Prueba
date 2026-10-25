"""Configuración que viene del entorno (variables de Render, tu .env, etc.)."""
import os


def normalize_url(url):
    """Render y otros proveedores dan a veces 'postgres://', formato que SQLAlchemy ya no acepta."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def database_url(project_root):
    """URL de la base de datos.

    En el plan gratuito de Render el disco se borra cada vez que el servicio se duerme,
    así que para conservar los datos hay que poner un Postgres en la variable DATABASE_URL.
    Sin ella se usa un SQLite local: sirve para desarrollar, pero en Render sería temporal.
    """
    url = normalize_url(os.environ.get("DATABASE_URL", ""))
    return url or "sqlite:///" + os.path.join(project_root, "app.db")
