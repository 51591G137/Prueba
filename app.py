"""Punto de entrada. Render lo arranca con: gunicorn app:app"""
from backend import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
