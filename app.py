"""Punto de entrada. Render lo arranca con: gunicorn app:app"""
import os

from backend import create_app

app = create_app()

if __name__ == "__main__":
    # ponytail: port 5001 by default on local machines to avoid macOS AirPlay conflict on port 5000
    port = int(os.environ.get("PORT", 5001))
    print(f"\n-> Servidor arrancado en: http://localhost:{port}\n")
    app.run(debug=True, port=port)
