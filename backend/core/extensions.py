"""Objetos compartidos por todos los módulos: base de datos y migraciones."""
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, event
from sqlalchemy.engine import Engine

# Nombres de restricciones predecibles: hacen que las migraciones sean estables
# y se puedan modificar más adelante tanto en SQLite como en Postgres.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION))
migrate = Migrate()


@event.listens_for(Engine, "connect")
def _sqlite_foreign_keys(dbapi_connection, _record):
    """SQLite ignora las claves foráneas salvo que se le pida; Postgres siempre las aplica.
    Así los borrados en cascada se comportan igual en local (SQLite) y en Render (Postgres)."""
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def skip_foreign_tables(obj, name, type_, reflected, compare_to):
    """Para `flask db migrate`: ignora las tablas que están en la base de datos pero no en los modelos
    (por ejemplo, las de otra app que comparta la misma base), así nunca propone borrarlas.
    Si algún día quitas un modelo y quieres borrar su tabla, escribe el `op.drop_table(...)` a mano."""
    return not (type_ == "table" and reflected and compare_to is None)
