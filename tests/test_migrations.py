"""Pruebas de las migraciones: actualización desde una base con restos de versiones anteriores
(se descartan, sin tocar tablas ajenas), reinicio, ida y vuelta y ausencia de cambios pendientes.

Desde la raíz del repositorio:
    python tests/test_migrations.py                    # con SQLite temporal
    TEST_DATABASE_URL=postgresql://usuario:clave@host/base_vacia python tests/test_migrations.py postgres
"""
import os
import sys
import tempfile

import sqlalchemy as sa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from flask_migrate import check, downgrade, upgrade  # noqa: E402

from backend import MIGRATIONS_DIR, create_app  # noqa: E402
from backend.core.config import normalize_url  # noqa: E402
from backend.core.extensions import db  # noqa: E402

kind = sys.argv[1] if len(sys.argv) > 1 else "sqlite"
url = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db") if kind == "sqlite" else os.environ["TEST_DATABASE_URL"]
OTHERS = {"auditoria_externa"}  # tabla ajena a la app: la migración no debe tocarla
EXPECTED = {"alembic_version", "bills", "customers", "items", "orders", "orders_item", "payment_methods",
            "reservations", "restaurants", "tables", "users", "users_restaurants"}
passed = 0


def ok(condition, label):
    global passed
    if not condition:
        print("  FALLO:", label)
        sys.exit(1)
    passed += 1


# 1) Una base de datos con restos de versiones anteriores: tablas de la versión 1, otras con nombres
#    de esta versión, otras que dependen de ellas (como un antiguo order_items -> menu_items) y una
#    tabla que no es de esta app y que no se debe tocar.
engine = sa.create_engine(normalize_url(url))
with engine.begin() as conn:
    for ddl in (
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name VARCHAR(80) NOT NULL)",
        "CREATE TABLE restaurants (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), name VARCHAR(120) NOT NULL)",
        "CREATE TABLE tables (id INTEGER PRIMARY KEY, restaurant_id INTEGER REFERENCES restaurants(id), name VARCHAR(40))",
        "CREATE TABLE menu_items (id INTEGER PRIMARY KEY, restaurant_id INTEGER REFERENCES restaurants(id), name VARCHAR(120))",
        "CREATE TABLE customers (id INTEGER PRIMARY KEY, name VARCHAR(80))",
        "CREATE TABLE reservations (id INTEGER PRIMARY KEY, table_id INTEGER REFERENCES tables(id), customer_id INTEGER REFERENCES customers(id))",
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, table_id INTEGER REFERENCES tables(id), status VARCHAR(20))",
        "CREATE TABLE order_items (id INTEGER PRIMARY KEY, order_id INTEGER REFERENCES orders(id), item_id INTEGER REFERENCES menu_items(id), quantity INTEGER)",
        "CREATE TABLE bills (id INTEGER PRIMARY KEY, table_id INTEGER REFERENCES tables(id), total NUMERIC(10,2))",
        "CREATE TABLE payment_methods (id INTEGER PRIMARY KEY, name VARCHAR(40))",
        "CREATE TABLE facilities (id INTEGER PRIMARY KEY, restaurant_id INTEGER REFERENCES restaurants(id), name VARCHAR(40))",
        "CREATE TABLE auditoria_externa (id INTEGER PRIMARY KEY, nota TEXT)",
        "INSERT INTO auditoria_externa (id, nota) VALUES (1, 'no me borres')",
        "INSERT INTO users (id, name) VALUES (1, 'Ana')",
        "INSERT INTO restaurants (id, user_id, name) VALUES (1, 1, 'Vieja Paella')",
        "INSERT INTO menu_items (id, restaurant_id, name) VALUES (1, 1, 'Paella')",
        "INSERT INTO order_items (id, item_id, quantity) VALUES (1, 1, 2)",
    ):
        conn.execute(sa.text(ddl))
engine.dispose()

# 2) La app arranca sobre esa base: migra y descarta lo antiguo
app = create_app({"DATABASE_URL": url})
with app.app_context():
    insp = sa.inspect(db.engine)
    ok(set(insp.get_table_names()) == EXPECTED | OTHERS, f"tablas tras migrar: {sorted(insp.get_table_names())}")
    ok("restaurant_id" in {c["name"] for c in insp.get_columns("orders")}, "orders es ya la tabla nueva")
    ok("username" in {c["name"] for c in insp.get_columns("users")}, "users tiene la columna nueva «username»")
    with db.engine.connect() as conn:
        ok(conn.execute(sa.text("SELECT COUNT(*) FROM users")).scalar() == 0, "los datos de prueba antiguos se descartan")
        ok(conn.execute(sa.text("SELECT nota FROM auditoria_externa")).scalar() == "no me borres", "la tabla ajena conserva sus datos")
        ok(conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar() == "0001", "versión de esquema 0001")
    check(directory=MIGRATIONS_DIR)  # lanza un error si los modelos y las migraciones no coinciden
    ok(True, "los modelos y las migraciones coinciden (sin cambios pendientes)")

# 3) Reiniciar sobre la misma base no hace nada ni falla
create_app({"DATABASE_URL": url})
ok(True, "segundo arranque sobre la misma base")

# 4) Ida y vuelta
with app.app_context():
    downgrade(directory=MIGRATIONS_DIR, revision="base")
    ok(set(sa.inspect(db.engine).get_table_names()) <= {"alembic_version"} | OTHERS, "downgrade deja la base vacía (salvo la tabla ajena)")
    upgrade(directory=MIGRATIONS_DIR)
    ok(set(sa.inspect(db.engine).get_table_names()) == EXPECTED | OTHERS, "upgrade tras downgrade")
    fks = {(t, fk["referred_table"], fk["options"].get("ondelete"))
           for t in sa.inspect(db.engine).get_table_names() for fk in sa.inspect(db.engine).get_foreign_keys(t)}
    for expected in [("orders_item", "orders", "CASCADE"), ("orders", "tables", "SET NULL"), ("bills", "tables", "SET NULL"),
                     ("reservations", "tables", "CASCADE"), ("tables", "restaurants", "CASCADE")]:
        ok(expected in fks, f"clave foránea {expected}")

print(f"OK: {passed} comprobaciones")
