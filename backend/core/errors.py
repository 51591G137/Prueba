"""Errores de la API: siempre se responden como JSON {"error": "mensaje"}."""
from flask import jsonify, request
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Error previsto. 400 = datos no válidos, 404 = no existe, 409 = la acción no es posible ahora."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return jsonify(error=err.message), err.status

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        if request.path.startswith("/api/"):
            message = "No encontrado." if err.code == 404 else err.description
            return jsonify(error=message), err.code
        return err
