# Mi Restaurante (versión de prueba)

Un único servidor Flask (Python) con dos apps web hechas en JavaScript, y dos APK de Android
que simplemente abren cada una de ellas:

| App | Dirección | Qué permite |
|---|---|---|
| Gestión (restaurantes) | `/restaurante/` | Crear usuarios, crear restaurantes, añadir mesas y platos al menú, ver las reservas por fecha y hora |
| Reservas (clientes) | `/cliente/` | Crear clientes, ver todos los restaurantes con sus mesas y menú, reservar una mesa para una fecha y hora |

Primera versión a propósito: **sin contraseñas ni permisos**. Se elige el usuario (o cliente) de una lista.

## Estructura

```
app.py                         backend: modelos, API JSON y rutas
requirements.txt               dependencias con versiones fijadas
.python-version                versión de Python que usará Render (3.13)
static/
  index.html                   inicio con enlaces a las dos apps
  restaurante.html / .js       app de gestión
  cliente.html / .js           app de clientes
  comun.js / estilos.css       código y estilos compartidos
.github/workflows/build-apk.yml   construye los dos APK
```

## Probar en el ordenador

```bash
python -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                      # abre http://127.0.0.1:5000
```

Sin configurar nada usa un SQLite local (`app.db`, ignorado por git).

## Render

Configuración del servicio web (la que ya tienes): **Build Command** `pip install -r requirements.txt`,
**Start Command** `gunicorn app:app`.

`.python-version` fija Python 3.13. Si en Render tienes definida una variable `PYTHON_VERSION`,
esa tiene prioridad.

### Que los datos no se pierdan (importante)

En el plan gratuito de Render el disco se borra cada vez que el servicio se duerme (a los
15 minutos sin visitas) o se reinicia. Con SQLite **todos los datos desaparecerían**. Para
conservarlos hace falta un Postgres:

1. En Render: **New +** > **PostgreSQL** > plan **Free**.
2. Cuando esté listo, copia su **Internal Database URL**.
3. En tu servicio web: **Environment** > añade `DATABASE_URL` con esa URL > guarda (se vuelve a desplegar).

La app crea las tablas sola. El Postgres gratuito de Render caduca a los 30 días de crearlo;
para algo duradero sirve cualquier otro Postgres: basta con poner su URL `postgresql://...`
en `DATABASE_URL`.

Aún no hay migraciones: si cambias los modelos de `app.py` con datos ya guardados, hay que
borrar las tablas afectadas (o crear una base de datos nueva) para que se vuelvan a crear.

### El primer arranque tarda

El servicio gratuito se duerme tras 15 minutos sin tráfico y despertar lleva hasta un minuto.
Los APK lo tienen en cuenta: mientras tanto muestran una pantalla "Conectando con el
servidor..." que reintenta sola.

## Construir los APK

1. Guarda `build-apk.yml` en `.github/workflows/` (sustituye al anterior).
2. En GitHub: **Actions** > **Construir APKs (restaurante y cliente)** > **Run workflow**.
3. Al terminar, en la página de la ejecución, descarga los artefactos `apk-restaurante` y
   `apk-cliente`. Cada zip contiene su `.apk`.
4. Instálalos en el móvil (hay que permitir "instalar apps desconocidas").

Cosas que conviene saber:

- **No hace falta reconstruir los APK cuando cambies el código.** Abren la web de Render, así
  que cualquier cambio llega con solo desplegar. Reconstruye únicamente si cambias el nombre,
  el identificador o la URL (arriba del workflow).
- Son APK de depuración y cada compilación se firma con una clave distinta: si ya tienes una
  versión instalada, desinstálala antes de instalar la nueva.
- Los dos tienen identificadores distintos (`com.mirestaurante.restaurante` y
  `com.mirestaurante.cliente`), así que pueden convivir en el mismo móvil.
- Si tu URL de Render no es `https://prueba-defz.onrender.com`, cámbiala en las dos entradas
  de la matriz del workflow.
- Versiones: Node 22, Java 21 y Capacitor 8.5.2 (Capacitor 8 necesita Node 22 o superior y Java 21).

## API

Todas devuelven JSON. Los errores tienen la forma `{"error": "mensaje"}` con código 400, 404 o 409.

| Método y ruta | Descripción |
|---|---|
| `GET/POST /api/users`, `GET /api/users/<id>` | Usuarios de la app de gestión |
| `GET/POST /api/customers`, `GET /api/customers/<id>` | Clientes |
| `GET/POST /api/users/<id>/restaurants` | Restaurantes de un usuario |
| `GET /api/restaurants`, `GET /api/restaurants/<id>` | Todos los restaurantes / uno |
| `GET/POST /api/restaurants/<id>/tables` | Mesas. Con `?date=AAAA-MM-DD&time=HH:MM` cada mesa indica `reserved` |
| `GET/POST /api/restaurants/<id>/menu` | Platos del menú |
| `GET /api/restaurants/<id>/reservations?date=AAAA-MM-DD[&time=HH:MM]` | Reservas de un día, opcionalmente de una hora |
| `POST /api/reservations` | Reservar: `customer_id`, `table_id`, `date`, `time`. Responde 409 si la mesa ya está reservada |

## Límites de esta versión

- Una reserva ocupa solo su franja exacta (las apps ofrecen franjas de 30 minutos, de 08:00 a 23:30).
  Todavía no hay duración ni solapes entre franjas.
- No se puede borrar ni editar nada (usuarios, restaurantes, mesas, platos ni reservas).
- No hay autenticación: cualquiera que conozca la dirección puede usar la API.
- Las fechas y horas son "de pared" (las que escribe la persona), sin zonas horarias.
