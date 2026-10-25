# Mi Restaurante (versión de prueba)

Un servidor Flask (Python) con dos apps web hechas en JavaScript, y dos APK de Android que solo
abren cada una de ellas. Primera versión a propósito **sin contraseñas ni permisos**: se elige el
usuario (o el cliente) de una lista.

| App | Dirección | Qué permite |
|---|---|---|
| Gestión | `/restaurante/` | Usuarios (crear, renombrar, borrar); restaurantes; mesas con estado libre u ocupada (crear, editar, borrar); menú (crear, editar, borrar); comandas por mesa, varias y con varios platos (crear, editar, borrar); emitir la factura de una mesa y cobrarla con un método de pago; métodos de pago; reservas por fecha y hora |
| Reservas | `/cliente/` | Crear clientes; ver restaurantes, mesas y menú; reservar mesa para una fecha y hora; ver, cambiar y cancelar sus reservas |

## Cómo funciona una mesa

1. Una mesa está **libre** hasta que tiene una comanda abierta (sin cobrar y no cancelada): entonces está **ocupada**. El estado no se guarda en la base de datos, se calcula, así nunca queda desincronizado.
2. Una mesa puede tener varias comandas y cada comanda varios platos. Mientras no estén en una factura se pueden editar o borrar.
3. **Emitir factura** junta los platos de todas las comandas abiertas de la mesa (suma los iguales). Una mesa tiene como mucho una factura pendiente; mientras exista no se pueden añadir ni modificar comandas.
4. **Cobrar** con un método de pago deja las comandas como pagadas y la mesa vuelve a estar **libre**. **Anular** una factura pendiente devuelve las comandas a abiertas. Una factura cobrada ya no se puede anular.
5. Una comanda **cancelada** no ocupa la mesa ni entra en las facturas, y ya solo se puede borrar.

Qué pasa al borrar:

- **Plato**: no se puede mientras esté en comandas sin cobrar. Las comandas y facturas antiguas guardan copia del nombre y del precio, así que no cambian. Cambiar el precio tampoco las altera.
- **Mesa**: no se puede si está ocupada. Sus reservas se borran con ella; las comandas y facturas cobradas se conservan como historial.
- **Usuario**: se borran también los restaurantes que solo gestionaba él, con todo lo que contienen (mesas, menú, comandas, facturas y reservas). Los restaurantes compartidos con otro usuario se conservan.
- **Reserva**: el cliente puede cambiar fecha, hora o mesa, o cancelarla.

## Estructura

```
app.py                       punto de entrada (Render: gunicorn app:app)
requirements.txt             dependencias con versiones fijadas
.python-version              Python 3.13 para Render
backend/                     el servidor, un módulo por tema
  core/                      base de datos, errores, validación, utilidades
  users/ customers/ restaurants/ tables/ menu/ payments/ orders/ billing/ reservations/
      models.py              tablas
      service.py             reglas de negocio (qué se puede y qué no)
      routes.py              direcciones de la API (traducen HTTP a llamadas al servicio)
  pages.py  routes.py        páginas HTML y registro de módulos
migrations/                  cambios de la base de datos (se aplican solos al arrancar)
static/
  restaurante.html  cliente.html  index.html
  css/                       base.css (colores, cabecera) y components.css (listas, botones, chips...)
  js/core/                   lo común: dom, api, router, ui, formato
  js/components/             piezas reutilizables: carta, selector de fecha y hora, cantidades
  js/restaurant/  js/customer/   una app cada una; main.js lista sus pantallas
docs/schema.dbml             el esquema real de la base de datos, en DBML
tests/                       pruebas del backend
.github/workflows/build-apk.yml
```

## Probar en el ordenador

```bash
python -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                      # abre http://127.0.0.1:5000
```

Sin configurar nada usa un SQLite local (`app.db`, ignorado por git). Las tablas se crean solas.

Pruebas del backend (desde la raíz del repositorio):

```bash
python tests/test_api.py           # reglas de negocio, validaciones, borrados en cascada, reservas
python tests/test_migrations.py    # migraciones
python tests/test_schema_doc.py    # docs/schema.dbml coincide con los modelos
```

## Render

Configuración del servicio web (la que ya tienes): **Build Command** `pip install -r requirements.txt`,
**Start Command** `gunicorn app:app`. `.python-version` fija Python 3.13; si en Render tienes definida
una variable `PYTHON_VERSION`, esa tiene prioridad.

### Que los datos no se pierdan (importante)

En el plan gratuito de Render el disco se borra cada vez que el servicio se duerme (a los 15 minutos
sin visitas) o se reinicia. Con SQLite **todos los datos desaparecerían**. Para conservarlos hace falta
un Postgres:

1. En Render: **New +** > **PostgreSQL** > plan **Free**.
2. Copia su **Internal Database URL**.
3. En tu servicio web: **Environment** > añade `DATABASE_URL` con esa URL > guarda (se vuelve a desplegar).

El Postgres gratuito de Render caduca a los 30 días de crearlo; para algo duradero sirve cualquier otro
Postgres: basta con poner su URL `postgresql://...` en `DATABASE_URL`.

### Al pasar de la versión 1 a esta

La primera migración (`0001`) **borra las tablas de la versión anterior y sus datos de prueba**, y crea
el esquema nuevo. Es lo único destructivo que hace. Si tu `DATABASE_URL` apuntaba a datos de la v1,
se descartan en el primer arranque. Las migraciones siguientes ya no borrarán datos.

Borra del repositorio los archivos que ya no se usan: `static/comun.js`, `static/restaurante.js`,
`static/cliente.js` y `static/estilos.css`.

## Base de datos y migraciones

Los cambios de la base de datos se guardan como migraciones en `migrations/versions/` y **se aplican
solas al arrancar la app** (en local y en Render). Para cambiar la base de datos:

1. Edita el modelo (`backend/<módulo>/models.py`).
2. Genera la migración: `flask --app app db migrate -m "descripción" --rev-id 0002` (el siguiente número libre).
3. Revisa el archivo creado y súbelo con el resto. Al desplegar se aplica sola.
4. Actualiza `docs/schema.dbml` (`python tests/test_schema_doc.py` avisa si no coincide).

`AUTO_MIGRATE=0` desactiva la migración automática al arrancar.

## Construir los APK

Sin cambios respecto a la versión anterior: **Actions** > **Construir APKs** > **Run workflow**. **No hace
falta reconstruirlos** al cambiar el código, porque abren la web de Render; solo si cambias el nombre, el
identificador o la URL del workflow. Son APK de depuración: si ya tienes uno instalado, desinstálalo antes de
instalar el nuevo.

## API

Todas devuelven JSON. Los errores tienen la forma `{"error": "mensaje"}` con código 400 (datos no válidos),
404 (no existe) o 409 (la acción no es posible en este momento).

| Método y ruta | Descripción |
|---|---|
| `GET POST /api/users` · `GET PATCH DELETE /api/users/<id>` | Usuarios; `DELETE` borra también sus restaurantes exclusivos |
| `GET POST /api/customers` · `GET /api/customers/<id>` | Clientes |
| `GET POST /api/users/<id>/restaurants` | Restaurantes de un usuario |
| `GET /api/restaurants` · `GET /api/restaurants/<id>` | Todos los restaurantes / uno |
| `GET POST /api/restaurants/<id>/tables` | Mesas con `status` libre u ocupada. Con `?date=AAAA-MM-DD&time=HH:MM` añade `reserved` |
| `GET PATCH DELETE /api/tables/<id>` | Una mesa (incluye `pending_bill` y nº de `reservations`) |
| `GET POST /api/restaurants/<id>/menu` · `GET PATCH DELETE /api/menu/<id>` | Menú |
| `GET POST /api/restaurants/<id>/payment-methods` | Métodos de pago |
| `GET POST /api/tables/<id>/orders` | Comandas sin cobrar de la mesa / crear (`user_id`, `items`, `requests`) |
| `GET PATCH DELETE /api/orders/<id>` | Una comanda (`items` sustituye los platos; `status`, `requests`) |
| `POST /api/tables/<id>/bills` | Emitir la factura de la mesa (`user_id`) |
| `GET DELETE /api/bills/<id>` · `POST /api/bills/<id>/pay` | Ver, anular (si está pendiente) y cobrar (`payment_method_id`) |
| `GET /api/restaurants/<id>/bills` | Facturas del restaurante |
| `POST /api/reservations` · `GET PATCH DELETE /api/reservations/<id>` | Reservas (`customer_id`, `table_id`, `date`, `time`) |
| `GET /api/customers/<id>/reservations[?from=AAAA-MM-DD]` | Reservas de un cliente |
| `GET /api/restaurants/<id>/reservations?date=AAAA-MM-DD[&time=HH:MM]` | Reservas de un día |

## Del esquema DBML a la base de datos

El esquema real está en `docs/schema.dbml`. Diferencias con el que diseñaste:

| En tu DBML | En la base de datos |
|---|---|
| `ORDERS` con `id_item`, `quantity`, `price` | `orders` es la comanda y `orders_item` sus líneas; plato, cantidad y precio viven en la línea |
| `Ref: ORDERS_ITEM.id_orders_item > ORDERS` | La clave foránea es `orders_item.order_id` (el DBML apuntaba desde la clave primaria) |
| `users.id_restaurant` y `users_restaurants` | Solo `users_restaurants`: un usuario puede gestionar varios restaurantes y un restaurante tener varios usuarios |
| `users` con email, contraseña, permisos | Solo `username`; el login llegará más adelante |
| `TABLES.status`, `facility_*` | El estado se calcula a partir de las comandas; `FACILITIES` no se ha implementado todavía |
| `BILLS.id_customer`, `ORDERS.id_customer` | Pendiente para cuando se integre al cliente en las comandas |
| `RESTAURANTS` con teléfono, coordenadas, logo, JSON | Solo `name` y `address` por ahora |
| `ITEMS` con `necesita_cocina`, `imagen_url` | Solo nombre, descripción y precio por ahora |
| (no estaba) | `customers` y `reservations`; copias de nombre y precio en `orders_item` y `bills.table_name`; `restaurant_id` en `orders` y `bills`, para conservar el historial y poder borrar en cascada |

## Añadir una función

- **Backend**: si es un tema nuevo, crea `backend/<tema>/` con `models.py`, `service.py` y `routes.py`, importa su modelo en `backend/models.py` y su blueprint en `backend/routes.py`, y genera la migración. Si es una regla nueva de un tema existente, normalmente solo cambia su `service.py`.
- **Frontend**: crea el archivo de la pantalla en `static/js/restaurant/` o `static/js/customer/`, expórtala como `async function view...({ params, stale })` y añade una línea en el `main.js` de esa app. Las piezas comunes están en `js/core/` y `js/components/`.
- Escribe una prueba en `tests/test_api.py` y ejecuta las tres de arriba.

## Pendiente

- Login y permisos; asociar al cliente con comandas y facturas; `FACILITIES`.
- Editar y borrar restaurantes y métodos de pago (por ahora solo se crean).
- Una reserva ocupa solo su franja exacta (las apps ofrecen franjas de 30 minutos, de 08:00 a 23:30); aún no hay duración ni solapes entre franjas.
- Sin autenticación, cualquiera que conozca la dirección puede usar la API.
- Las fechas y horas de las reservas son "de pared" (las que escribe la persona), sin zonas horarias; las de comandas y facturas se guardan en UTC y se muestran en la hora del móvil.
