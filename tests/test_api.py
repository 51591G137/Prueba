"""Pruebas de la API: reglas de negocio, validaciones, borrados en cascada, historial y reservas.

Desde la raíz del repositorio:
    python tests/test_api.py                    # con una base SQLite temporal
    TEST_DATABASE_URL=postgresql://usuario:clave@host/base_vacia python tests/test_api.py postgres
(con Postgres la base debe estar VACÍA; además se prueban 20 reservas simultáneas)
"""
import os
import sys
import tempfile
import threading
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from backend import create_app  # noqa: E402
from backend.billing.models import Bill  # noqa: E402
from backend.core.extensions import db  # noqa: E402
from backend.models import (Customer, Item, Order, OrderItem, PaymentMethod, Reservation, Restaurant,  # noqa: E402
                            RestaurantTable, User, UserRestaurant)

kind = sys.argv[1] if len(sys.argv) > 1 else "sqlite"
if kind == "sqlite":
    url = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "test.db")
else:
    url = os.environ["TEST_DATABASE_URL"]

app = create_app({"DATABASE_URL": url})
c = app.test_client()
passed = 0


def check(label, cond, extra=""):
    global passed
    if not cond:
        print(f"  FALLO: {label} {extra}")
        sys.exit(1)
    passed += 1


def post(path, **payload):
    return c.post(path, json=payload)


def patch(path, **payload):
    return c.patch(path, json=payload)


def get(path):
    return c.get(path)


def count(model, **filters):
    with app.app_context():
        return model.query.filter_by(**filters).count()


def err(resp, status, fragment=""):
    return resp.status_code == status and fragment in (resp.get_json() or {}).get("error", "")


print(f"== API v2 sobre {kind}")

# --- páginas ---------------------------------------------------------------------------
for path in ("/", "/restaurante/", "/cliente/", "/health"):
    check(f"GET {path}", get(path).status_code == 200)
check("ruta API inexistente -> JSON", err(get("/api/nada"), 404, "No encontrado"))
check("método no permitido -> JSON", c.delete("/api/users").status_code == 405)

# --- usuarios --------------------------------------------------------------------------
ana = post("/api/users", username="  Ana  ").get_json()
check("crear usuario", ana == {"id": 1, "username": "Ana"}, ana)
check("username obligatorio", err(post("/api/users", username=""), 400, "obligatorio"))
check("username largo", err(post("/api/users", username="x" * 81), 400, "80"))
check("get usuario", get("/api/users/1").get_json() == ana)
r = patch("/api/users/1", username="Ana María")
check("renombrar usuario", r.status_code == 200 and r.get_json()["username"] == "Ana María")
check("renombrar con nombre vacío", err(patch("/api/users/1", username=" "), 400))
check("renombrar usuario inexistente", patch("/api/users/99", username="x").status_code == 404)
luis = post("/api/users", username="Luis").get_json()
r = c.delete(f"/api/users/{luis['id']}")
check("borrar usuario sin restaurantes", r.get_json() == {"deleted": True, "restaurants_deleted": 0})
check("lista de usuarios", [u["username"] for u in get("/api/users").get_json()] == ["Ana María"])

# auth personal del restaurante (Bearer tokens y restablecimiento de contraseña)
carlos = post("/api/users", username="Carlos", email="carlos@ejemplo.com", password="secret123").get_json()
check("crear usuario con contraseña y email", carlos["username"] == "Carlos" and carlos["email"] == "carlos@ejemplo.com")
check("usuario duplicado", err(post("/api/users", username="Carlos"), 409, "ya está en uso"))
check("email duplicado", err(post("/api/users", username="Carlos2", email="carlos@ejemplo.com"), 409, "ya está registrado"))
check("login contraseña incorrecta", err(post("/api/auth/login", username="Carlos", password="wrong"), 401, "incorrectos"))
login_res = post("/api/auth/login", username="Carlos", password="secret123")
check("login correcto devuelve token Bearer", login_res.status_code == 200 and "token" in login_res.get_json())
token = login_res.get_json()["token"]
# comprobar autenticación vía cabecera Bearer sin cookie de sesión
c_client = app.test_client()  # nuevo cliente HTTP limpio sin cookies
bearer_res = c_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
check("autenticación por Bearer header", bearer_res.status_code == 200 and bearer_res.get_json()["username"] == "Carlos")
check("Bearer header inválido -> 401", c_client.get("/api/auth/me", headers={"Authorization": "Bearer token_falso"}).status_code == 401)
check("logout web", post("/api/auth/logout").status_code == 200)

# recuperación de contraseña por email (self-service reset)
forgot = post("/api/auth/forgot-password", email="carlos@ejemplo.com").get_json()
check("solicitar restablecimiento genera token", forgot["ok"] is True and bool(forgot["token"]))
reset_token = forgot["token"]
check("restablecer contraseña con token", post("/api/auth/reset-password", token=reset_token, password="newsecret456").status_code == 200)
check("login con contraseña antigua falla", err(post("/api/auth/login", username="Carlos", password="secret123"), 401, "incorrectos"))
check("login con contraseña nueva funciona", post("/api/auth/login", username="Carlos", password="newsecret456").status_code == 200)
check("token de reseteo inválido falla", err(post("/api/auth/reset-password", token="invalido", password="abc"), 400, "inválido"))
c.delete(f"/api/users/{carlos['id']}")

# --- restaurantes ----------------------------------------------------------------------
rest = post("/api/users/1/restaurants", name="La Paella", address="Calle Mayor 1").get_json()
check("crear restaurante", rest == {"id": 1, "name": "La Paella", "address": "Calle Mayor 1"}, rest)
check("restaurante de usuario inexistente", post("/api/users/99/restaurants", name="x").status_code == 404)
check("restaurantes del usuario", [x["name"] for x in get("/api/users/1/restaurants").get_json()] == ["La Paella"])
check("todos los restaurantes", len(get("/api/restaurants").get_json()) == 1)
RID = rest["id"]

# --- mesas -----------------------------------------------------------------------------
t1 = post(f"/api/restaurants/{RID}/tables", name="Mesa 1", capacity=4).get_json()
t2 = post(f"/api/restaurants/{RID}/tables", name="Mesa 2", capacity="2").get_json()
check("crear mesa", t1 == {"id": 1, "restaurant_id": 1, "name": "Mesa 1", "capacity": 4, "status": "libre"}, t1)
for bad in (0, 51, "abc", None, 2.5, True):
    check(f"capacidad inválida {bad!r}", post(f"/api/restaurants/{RID}/tables", name="X", capacity=bad).status_code == 400)
check("estado libre al crear", [t["status"] for t in get(f"/api/restaurants/{RID}/tables").get_json()] == ["libre", "libre"])
d = get("/api/tables/1").get_json()
check("detalle de mesa", d["pending_bill"] is None and d["reservations"] == 0 and d["status"] == "libre", d)
r = patch("/api/tables/1", name="Mesa Ventana", capacity=6)
check("editar mesa", r.get_json()["name"] == "Mesa Ventana" and r.get_json()["capacity"] == 6)
check("editar mesa: capacidad inválida", err(patch("/api/tables/1", capacity=0), 400))
check("editar mesa: nombre vacío", err(patch("/api/tables/1", name=""), 400))
check("editar mesa inexistente", patch("/api/tables/99", name="x").status_code == 404)
patch("/api/tables/1", name="Mesa 1", capacity=4)

# --- menú ------------------------------------------------------------------------------
paella = post(f"/api/restaurants/{RID}/menu", name="Paella", description="Arroz", price="14.5").get_json()
agua = post(f"/api/restaurants/{RID}/menu", name="Agua", price="2").get_json()
flan = post(f"/api/restaurants/{RID}/menu", name="Flan", price=3.5).get_json()
check("crear plato", paella == {"id": 1, "restaurant_id": 1, "name": "Paella", "description": "Arroz", "price": 14.5}, paella)
check("precio inválido", err(post(f"/api/restaurants/{RID}/menu", name="Mal", price="abc"), 400, "precio"))
r = patch("/api/menu/3", name="Flan casero", description="", price="4,25")
check("editar plato (nombre, descripción vacía, precio con coma)",
      r.get_json() == {"id": 3, "restaurant_id": 1, "name": "Flan casero", "description": None, "price": 4.25}, r.get_json())
check("editar plato: precio inválido", err(patch("/api/menu/3", price=-1), 400))
check("editar plato inexistente", patch("/api/menu/99", name="x").status_code == 404)
check("get plato", get("/api/menu/1").get_json()["name"] == "Paella")
r = c.delete("/api/menu/3")
check("borrar plato sin comandas", r.get_json() == {"deleted": True} and get("/api/menu/3").status_code == 404)
check("menú tras borrar", [i["name"] for i in get(f"/api/restaurants/{RID}/menu").get_json()] == ["Paella", "Agua"])

# --- métodos de pago -------------------------------------------------------------------
check("sin métodos de pago", get(f"/api/restaurants/{RID}/payment-methods").get_json() == [])
efectivo = post(f"/api/restaurants/{RID}/payment-methods", name="Efectivo").get_json()
post(f"/api/restaurants/{RID}/payment-methods", name="Bizum")
check("método duplicado (sin distinguir mayúsculas)", err(post(f"/api/restaurants/{RID}/payment-methods", name="EFECTIVO"), 409, "Ya existe"))
check("método sin nombre", err(post(f"/api/restaurants/{RID}/payment-methods", name=""), 400))
check("lista de métodos", [m["name"] for m in get(f"/api/restaurants/{RID}/payment-methods").get_json()] == ["Efectivo", "Bizum"])

# --- comandas --------------------------------------------------------------------------
def order_payload(items, **extra):
    return {"user_id": 1, "items": [{"item_id": i, "quantity": q} for i, q in items], **extra}


r = c.post("/api/tables/1/orders", json=order_payload([(1, 2), (2, 1)], requests="sin sal"))
o1 = r.get_json()
check("crear comanda", r.status_code == 201 and o1["total"] == 31.0 and o1["status"] == "pedido" and not o1["is_paid"], o1)
check("líneas de la comanda", [(l["name"], l["quantity"], l["unit_price"], l["subtotal"]) for l in o1["lines"]]
      == [("Paella", 2, 14.5, 29.0), ("Agua", 1, 2.0, 2.0)], o1["lines"])
check("notas guardadas", o1["requests"] == "sin sal" and o1["created_at"].endswith("Z") and o1["user_id"] == 1)
check("mesa ocupada con una comanda", get("/api/tables/1").get_json()["status"] == "ocupada")
check("la otra mesa sigue libre", get("/api/tables/2").get_json()["status"] == "libre")
check("estado en el listado", [(t["name"], t["status"]) for t in get(f"/api/restaurants/{RID}/tables").get_json()]
      == [("Mesa 1", "ocupada"), ("Mesa 2", "libre")])
check("platos repetidos se suman", c.post("/api/tables/2/orders", json=order_payload([(2, 1), (2, 2)])).get_json()["lines"][0]["quantity"] == 3)
check("sin platos", err(c.post("/api/tables/1/orders", json={"user_id": 1, "items": []}), 400, "al menos un plato"))
check("sin lista de platos", err(c.post("/api/tables/1/orders", json={"user_id": 1}), 400))
check("cantidad 0", c.post("/api/tables/1/orders", json=order_payload([(1, 0)])).status_code == 400)
check("cantidad 100", c.post("/api/tables/1/orders", json=order_payload([(1, 100)])).status_code == 400)
check("suma de repetidos pasa de 99", c.post("/api/tables/1/orders", json=order_payload([(1, 60), (1, 60)])).status_code == 400)
check("plato inexistente", err(c.post("/api/tables/1/orders", json=order_payload([(99, 1)])), 404, "ya no existe"))
check("sin usuario", c.post("/api/tables/1/orders", json={"items": [{"item_id": 1, "quantity": 1}]}).status_code == 400)
check("usuario inexistente", err(c.post("/api/tables/1/orders", json={**order_payload([(1, 1)]), "user_id": 99}), 404, "usuario"))
check("mesa inexistente", c.post("/api/tables/99/orders", json=order_payload([(1, 1)])).status_code == 404)
# plato de otro restaurante
rest2 = post("/api/users/1/restaurants", name="Otro").get_json()
foreign = post(f"/api/restaurants/{rest2['id']}/menu", name="Ajeno", price=5).get_json()
check("plato de otro restaurante", err(c.post("/api/tables/1/orders", json=order_payload([(foreign["id"], 1)])), 404, "ya no existe"))
check("tras los errores solo existen las comandas esperadas", len(get("/api/tables/1/orders").get_json()) == 1)
c.delete("/api/orders/2")  # borra la comanda de prueba de la mesa 2 (agua x3)

# Comanda 3 (en la mesa 1): agua x3, luego cambia el precio del agua y se edita
o2 = c.post("/api/tables/1/orders", json=order_payload([(2, 3)])).get_json()
check("segunda comanda en la misma mesa", o2["id"] != o1["id"] and o2["total"] == 6.0, o2)
patch("/api/menu/2", price="2.5")
r = patch(f"/api/orders/{o2['id']}", items=[{"item_id": 2, "quantity": 1}, {"item_id": 1, "quantity": 1}], user_id=1, requests="")
o2 = r.get_json()
check("editar comanda: la línea existente conserva su precio, la nueva usa el actual",
      [(l["name"], l["quantity"], l["unit_price"]) for l in o2["lines"]] == [("Agua", 1, 2.0), ("Paella", 1, 14.5)], o2["lines"])
check("editar comanda: total y notas vacías", o2["total"] == 16.5 and o2["requests"] is None)
check("editar estado", patch(f"/api/orders/{o2['id']}", status="en_preparacion").get_json()["status"] == "en_preparacion")
check("estado inválido", err(patch(f"/api/orders/{o2['id']}", status="volando"), 400, "estado"))
check("editar con lista vacía", err(patch(f"/api/orders/{o2['id']}", items=[]), 400))
check("editar con plato ajeno", patch(f"/api/orders/{o2['id']}", items=[{"item_id": foreign["id"], "quantity": 1}]).status_code == 404)
check("get comanda", get(f"/api/orders/{o2['id']}").get_json()["status"] == "en_preparacion")
o3 = c.post("/api/tables/1/orders", json=order_payload([(2, 1)])).get_json()  # agua al precio nuevo (2.5)
check("tercera comanda con el precio actualizado", o3["lines"][0]["unit_price"] == 2.5 and o3["total"] == 2.5)
check("lista de comandas sin cobrar de la mesa", [o["id"] for o in get("/api/tables/1/orders").get_json()] == [o1["id"], o2["id"], o3["id"]])

# Cancelar: no ocupa la mesa y ya no se puede editar
t2_order = c.post("/api/tables/2/orders", json=order_payload([(1, 1)])).get_json()
check("mesa 2 ocupada", get("/api/tables/2").get_json()["status"] == "ocupada")
check("cancelar comanda", patch(f"/api/orders/{t2_order['id']}", status="cancelado").get_json()["status"] == "cancelado")
check("una comanda cancelada no ocupa la mesa", get("/api/tables/2").get_json()["status"] == "libre")
check("cancelada: ya no se edita", err(patch(f"/api/orders/{t2_order['id']}", requests="x"), 409, "cancelada"))
check("cancelada: se puede borrar", c.delete(f"/api/orders/{t2_order['id']}").status_code == 200)
check("la comanda borrada no existe", get(f"/api/orders/{t2_order['id']}").status_code == 404)
check("borrar la comanda borra sus líneas", count(OrderItem, order_id=t2_order["id"]) == 0)

# --- facturas --------------------------------------------------------------------------
check("facturar mesa sin comandas", err(post("/api/tables/2/bills", user_id=1), 409, "No hay comandas"))
check("facturar sin usuario", post("/api/tables/1/bills").status_code == 400)
r = post("/api/tables/1/bills", user_id=1)
bill = r.get_json()
check("emitir factura", r.status_code == 201 and bill["status"] == "pendiente" and bill["total"] == 50.0 and bill["table"] == "Mesa 1", bill)
check("la factura junta los platos de todas las comandas (suma los iguales)",
      [(l["name"], l["unit_price"], l["quantity"], l["subtotal"]) for l in bill["lines"]]
      == [("Paella", 14.5, 3, 43.5), ("Agua", 2.0, 2, 4.0), ("Agua", 2.5, 1, 2.5)], bill["lines"])
check("sin cobrar: cierre y método vacíos", bill["close_datetime"] is None and bill["payment_method"] is None)
check("las comandas quedan en la factura", {o["bill_id"] for o in get("/api/tables/1/orders").get_json()} == {bill["id"]})
check("segunda factura mientras hay una pendiente", err(post("/api/tables/1/bills", user_id=1), 409, "pendiente"))
check("con factura pendiente no se añaden comandas", err(c.post("/api/tables/1/orders", json=order_payload([(1, 1)])), 409, "factura pendiente"))
check("con factura pendiente no se edita", err(patch(f"/api/orders/{o1['id']}", requests="x"), 409, "factura"))
check("con factura pendiente no se borra", err(c.delete(f"/api/orders/{o1['id']}"), 409, "factura"))
check("la mesa sigue ocupada", get("/api/tables/1").get_json()["status"] == "ocupada")
check("detalle de mesa con factura pendiente", get("/api/tables/1").get_json()["pending_bill"] == {"id": bill["id"], "total": 50.0})
check("no se borra una mesa ocupada", err(c.delete("/api/tables/1"), 409, "ocupada"))
check("get factura", get(f"/api/bills/{bill['id']}").get_json()["lines"] == bill["lines"])
check("lista de facturas", [b["status"] for b in get(f"/api/restaurants/{RID}/bills").get_json()] == ["pendiente"])

# Anular y volver a emitir
check("anular factura pendiente", c.delete(f"/api/bills/{bill['id']}").get_json() == {"deleted": True})
check("al anular, las comandas vuelven a estar abiertas", {o["bill_id"] for o in get("/api/tables/1/orders").get_json()} == {None})
check("tras anular se puede editar", patch(f"/api/orders/{o1['id']}", requests="con sal").status_code == 200)
check("tras anular se pueden añadir comandas", c.post("/api/tables/1/orders", json=order_payload([(2, 1)])).status_code == 201)
c.delete(f"/api/orders/{get('/api/tables/1/orders').get_json()[-1]['id']}")
bill = post("/api/tables/1/bills", user_id=1).get_json()
check("nueva factura tras anular", bill["total"] == 50.0 and bill["status"] == "pendiente")

# Cobrar
check("cobrar sin método de pago", err(post(f"/api/bills/{bill['id']}/pay"), 400, "método"))
other_method = post(f"/api/restaurants/{rest2['id']}/payment-methods", name="Tarjeta").get_json()
check("método de otro restaurante", err(post(f"/api/bills/{bill['id']}/pay", payment_method_id=other_method["id"]), 404, "método"))
check("método inexistente", post(f"/api/bills/{bill['id']}/pay", payment_method_id=999).status_code == 404)
r = post(f"/api/bills/{bill['id']}/pay", payment_method_id=efectivo["id"])
paid = r.get_json()
check("cobrar factura", r.status_code == 200 and paid["status"] == "pagada" and paid["payment_method"] == "Efectivo" and paid["close_datetime"].endswith("Z"), paid)
check("la mesa vuelve a estar libre al cobrar", get("/api/tables/1").get_json()["status"] == "libre")
check("no quedan comandas sin cobrar", get("/api/tables/1/orders").get_json() == [])
check("las comandas quedan pagadas", count(Order, table_id=1, is_paid=True) == 3 and count(Order, table_id=1, is_paid=False) == 0)
check("cobrar dos veces", err(post(f"/api/bills/{bill['id']}/pay", payment_method_id=efectivo["id"]), 409, "ya está cobrada"))
check("anular una factura cobrada", err(c.delete(f"/api/bills/{bill['id']}"), 409, "cobrada"))
check("las comandas pagadas no se editan ni borran", patch(f"/api/orders/{o1['id']}", requests="x").status_code == 409
      and c.delete(f"/api/orders/{o1['id']}").status_code == 409)
check("detalle sin factura pendiente", get("/api/tables/1").get_json()["pending_bill"] is None)

# Segunda ronda en la misma mesa: la factura solo incluye las comandas nuevas
c.post("/api/tables/1/orders", json=order_payload([(1, 1)]))
check("la mesa vuelve a ocuparse", get("/api/tables/1").get_json()["status"] == "ocupada")
bill2 = post("/api/tables/1/bills", user_id=1).get_json()
check("la segunda factura solo tiene las comandas nuevas", bill2["total"] == 14.5 and len(bill2["lines"]) == 1, bill2)
post(f"/api/bills/{bill2['id']}/pay", payment_method_id=2)
check("lista de facturas (más reciente primero)",
      [(b["id"], b["status"], b["payment_method"]) for b in get(f"/api/restaurants/{RID}/bills").get_json()]
      == [(bill2["id"], "pagada", "Bizum"), (bill["id"], "pagada", "Efectivo")])

# --- borrar platos con comandas --------------------------------------------------------
c.post("/api/tables/2/orders", json=order_payload([(1, 1)]))
check("no se borra un plato en comandas sin cobrar", err(c.delete("/api/menu/1"), 409, "sin cobrar"))
open_id = get("/api/tables/2/orders").get_json()[0]["id"]
c.delete(f"/api/orders/{open_id}")
check("se borra cuando solo está en comandas cobradas", c.delete("/api/menu/1").status_code == 200)
check("la factura cobrada conserva el plato borrado", get(f"/api/bills/{bill['id']}").get_json()["lines"][0]["name"] == "Paella")
with app.app_context():
    check("la línea guarda el nombre y deja de apuntar al plato", OrderItem.query.filter_by(item_name="Paella", item_id=None).count() >= 3)

# --- reservas --------------------------------------------------------------------------
maria = post("/api/customers", name="María").get_json()
pedro = post("/api/customers", name="Pedro").get_json()
D, T = "2026-11-20", "21:00"
r = post("/api/reservations", customer_id=maria["id"], table_id=2, date=D, time=T)
res = r.get_json()
check("reservar", r.status_code == 201 and res["customer"] == "María" and res["table"] == "Mesa 2" and res["restaurant"] == "La Paella" and res["time"] == T, res)
check("misma mesa y hora: conflicto", err(post("/api/reservations", customer_id=pedro["id"], table_id=2, date=D, time=T), 409, "ya está reservada"))
check("estado de las mesas en esa franja", [(t["name"], t["reserved"]) for t in get(f"/api/restaurants/{RID}/tables?date={D}&time={T}").get_json()]
      == [("Mesa 1", False), ("Mesa 2", True)])
check("al editar se ignora la propia reserva", get(f"/api/restaurants/{RID}/tables?date={D}&time={T}&exclude_reservation={res['id']}").get_json()[1]["reserved"] is False)
check("get reserva", get(f"/api/reservations/{res['id']}").get_json() == res)
check("reserva inexistente", get("/api/reservations/99").status_code == 404)
p = post("/api/reservations", customer_id=pedro["id"], table_id=1, date=D, time="22:00").get_json()
# editar
r = patch(f"/api/reservations/{res['id']}", time="20:30")
check("cambiar la hora", r.status_code == 200 and r.get_json()["time"] == "20:30" and r.get_json()["table"] == "Mesa 2")
check("cambiar la fecha", patch(f"/api/reservations/{res['id']}", date="2026-11-21").get_json()["date"] == "2026-11-21")
check("cambiar de mesa", patch(f"/api/reservations/{res['id']}", table_id=1, date=D, time="20:30").get_json()["table"] == "Mesa 1")
check("cambiar a una franja ocupada", err(patch(f"/api/reservations/{res['id']}", time="22:00"), 409, "ya está reservada"))
check("no cuenta como conflicto consigo misma", patch(f"/api/reservations/{res['id']}", time="20:30").status_code == 200)
foreign_table = post(f"/api/restaurants/{rest2['id']}/tables", name="Ajena", capacity=2).get_json()
check("mesa de otro restaurante", err(patch(f"/api/reservations/{res['id']}", table_id=foreign_table["id"]), 404, "mesa"))
check("hora inválida", err(patch(f"/api/reservations/{res['id']}", time="25:00"), 400, "hora"))
check("fecha inválida", err(patch(f"/api/reservations/{res['id']}", date="mañana"), 400, "fecha"))
check("tras los errores la reserva sigue igual", get(f"/api/reservations/{res['id']}").get_json()["time"] == "20:30")
# listas
check("reservas del cliente ordenadas", [(x["date"], x["time"]) for x in get(f"/api/customers/{maria['id']}/reservations").get_json()] == [(D, "20:30")])
post("/api/reservations", customer_id=maria["id"], table_id=2, date="2026-12-01", time="14:00")
post("/api/reservations", customer_id=maria["id"], table_id=2, date="2026-10-01", time="14:00")
check("reservas del cliente (todas, por fecha)", [x["date"] for x in get(f"/api/customers/{maria['id']}/reservations").get_json()] == ["2026-10-01", D, "2026-12-01"])
check("reservas del cliente desde una fecha", [x["date"] for x in get(f"/api/customers/{maria['id']}/reservations?from=2026-11-01").get_json()] == [D, "2026-12-01"])
check("reservas de otro cliente", [x["customer"] for x in get(f"/api/customers/{pedro['id']}/reservations").get_json()] == ["Pedro"])
check("cliente inexistente", get("/api/customers/99/reservations").status_code == 404)
check("reservas del restaurante por día", [(x["time"], x["table"], x["customer"]) for x in get(f"/api/restaurants/{RID}/reservations?date={D}").get_json()]
      == [("20:30", "Mesa 1", "María"), ("22:00", "Mesa 1", "Pedro")])
check("reservas del restaurante por hora", [x["customer"] for x in get(f"/api/restaurants/{RID}/reservations?date={D}&time=22:00").get_json()] == ["Pedro"])
check("reservas sin fecha", get(f"/api/restaurants/{RID}/reservations").status_code == 400)
# reservas con sólo teléfono (auth sin contraseña de clientes)
ana_res = post("/api/reservations", phone="611222333", name="Ana", table_id=2, date="2026-11-25", time="21:00")
check("reservar directamente con teléfono", ana_res.status_code == 201 and ana_res.get_json()["phone"] == "611222333" and ana_res.get_json()["customer"] == "Ana")
ana_res2 = post("/api/reservations", phone="611222333", table_id=2, date="2026-11-26", time="21:00")
check("segunda reserva reutiliza cliente por teléfono", ana_res2.status_code == 201 and ana_res2.get_json()["customer_id"] == ana_res.get_json()["customer_id"])
ana_bookings = get("/api/customers/by-phone/611222333/reservations").get_json()
check("listar reservas por teléfono", len(ana_bookings) == 2 and ana_bookings[0]["phone"] == "611222333")
ana_customer = get("/api/customers/by-phone/611222333").get_json()
check("obtener cliente por teléfono", ana_customer["name"] == "Ana" and ana_customer["phone"] == "611222333")
c.delete(f"/api/reservations/{ana_res.get_json()['id']}")
c.delete(f"/api/reservations/{ana_res2.get_json()['id']}")
with app.app_context():
    db.session.delete(Customer.query.filter_by(phone="611222333").first())
    db.session.commit()
# borrar
check("detalle de mesa cuenta reservas", get("/api/tables/2").get_json()["reservations"] == 2)
check("cancelar reserva", c.delete(f"/api/reservations/{p['id']}").get_json() == {"deleted": True})
check("la reserva cancelada libera la franja", post("/api/reservations", customer_id=maria["id"], table_id=1, date=D, time="22:00").status_code == 201)
check("cancelar reserva inexistente", c.delete("/api/reservations/999").status_code == 404)

# --- borrar mesa: conserva el historial y borra las reservas ----------------------------
check("la mesa 1 tiene reservas", get("/api/tables/1").get_json()["reservations"] == 2)
check("borrar mesa libre", c.delete("/api/tables/1").get_json() == {"deleted": True})
check("sus reservas se borran con ella", count(Reservation, table_id=1) == 0)
bills = get(f"/api/restaurants/{RID}/bills").get_json()
check("las facturas conservan el nombre de la mesa borrada", [(b["table"], b["table_id"], b["status"]) for b in bills] == [("Mesa 1", None, "pagada")] * 2, bills)
check("las comandas cobradas se conservan sin mesa", count(Order, table_id=None, is_paid=True) == 4)
check("las reservas de otras mesas siguen", count(Reservation, table_id=2) == 2)
check("mesa borrada", get("/api/tables/1").status_code == 404)

# --- borrar usuario: restaurantes exclusivos en cascada, compartidos se conservan -------
# restaurante compartido con Luis (segundo usuario)
luis = post("/api/users", username="Luis").get_json()
shared = post("/api/users/1/restaurants", name="Compartido").get_json()
with app.app_context():
    db.session.add(UserRestaurant(user_id=luis["id"], restaurant_id=shared["id"]))
    db.session.commit()
mesa_s = post(f"/api/restaurants/{shared['id']}/tables", name="S1", capacity=2).get_json()
post(f"/api/restaurants/{RID}/payment-methods", name="Tarjeta")
c.post("/api/tables/2/orders", json=order_payload([(2, 2)]))  # comanda abierta en el restaurante exclusivo de Ana
post("/api/tables/2/bills", user_id=1)  # factura pendiente
check("antes de borrar existen datos del restaurante 1", count(Order, restaurant_id=RID) >= 1 and count(Bill, restaurant_id=RID) >= 1)
r = c.delete("/api/users/1")
check("borrar usuario: cuenta los restaurantes borrados (no el compartido)", r.get_json() == {"deleted": True, "restaurants_deleted": 2}, r.get_json())
# restaurantes 1 y 2 ("La Paella" y "Otro") eran solo de Ana; "Compartido" también lo gestiona Luis
with app.app_context():
    for model in (RestaurantTable, Item, Order, Bill, PaymentMethod, UserRestaurant):
        check(f"cascada: no quedan {model.__tablename__} de los restaurantes borrados",
              model.query.filter(model.restaurant_id.in_([RID, rest2["id"]])).count() == 0)
    check("cascada: no quedan líneas ni reservas huérfanas",
          OrderItem.query.count() == 0 and Reservation.query.count() == 0)
    check("el restaurante compartido sobrevive", db.session.get(Restaurant, shared["id"]) is not None)
    check("y su mesa", db.session.get(RestaurantTable, mesa_s["id"]) is not None)
    check("y el vínculo de Luis", UserRestaurant.query.filter_by(user_id=luis["id"], restaurant_id=shared["id"]).count() == 1)
    check("los clientes no se tocan", Customer.query.count() == 2)
check("el usuario ya no existe", get("/api/users/1").status_code == 404)
check("los clientes ya no ven los restaurantes borrados", [r["name"] for r in get("/api/restaurants").get_json()] == ["Compartido"])
check("las reservas del cliente se han ido con las mesas", get(f"/api/customers/{maria['id']}/reservations").get_json() == [])

# --- concurrencia (solo con Postgres: SQLite serializa las escrituras) -------------------
if kind == "postgres":
    rest3 = post(f"/api/users/{luis['id']}/restaurants", name="Concurrencia").get_json()
    mesa_c = post(f"/api/restaurants/{rest3['id']}/tables", name="C1", capacity=2).get_json()
    codes, barrier = [], threading.Barrier(20)

    def worker(i):
        client = app.test_client()
        barrier.wait()
        codes.append(client.post("/api/reservations", json={"customer_id": maria["id"], "table_id": mesa_c["id"],
                                                             "date": "2031-05-05", "time": "20:00"}).status_code)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    check("20 reservas simultáneas: una gana y el resto recibe 409, sin errores 500",
          Counter(codes) == Counter({201: 1, 409: 19}), Counter(codes))

print(f"OK: {passed} comprobaciones")
