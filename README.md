# Prueba Restaurante - MVP

Backend Flask + dos frontends (restaurante y cliente) + construcción automática de APKs con Capacitor.

## 🚀 Despliegue en Render

1. Crea un servicio **Web** en Render conectado a este repositorio.
2. Añade una base de datos **PostgreSQL** gratuita en Render.
3. En el servicio web, configura la variable de entorno `DATABASE_URL` (Render la inyecta automáticamente al vincular la base de datos).
4. Comando de arranque: `gunicorn app:app`.

## 📱 Generar APKs

Ve a la pestaña **Actions** de GitHub, selecciona **Construir APKs (Restaurante y Cliente)** y pulsa **Run workflow**.  
Al finalizar, descarga los artefactos `apk-restaurant` y `apk-client`.

## 🔧 Desarrollo local

```bash
pip install -r requirements.txt
python app.py