"""Lectura y validación de los datos que llegan en las peticiones."""
import math
from datetime import datetime

from flask import request

from .errors import ApiError

MAX_ID = 2**31 - 1


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def text_field(data, key, label, max_len, required=True):
    value = data.get(key)
    value = value.strip() if isinstance(value, str) else ""
    if required and not value:
        raise ApiError(f"{label} es obligatorio.")
    if len(value) > max_len:
        raise ApiError(f"{label} no puede superar {max_len} caracteres.")
    return value or None


def int_field(data, key, label, minimum, maximum):
    try:
        value = int(str(data.get(key)).strip())
    except ValueError:
        raise ApiError(f"{label} debe ser un número entero.")
    if not minimum <= value <= maximum:
        raise ApiError(f"{label} debe estar entre {minimum} y {maximum}.")
    return value


def id_field(data, key, label):
    return int_field(data, key, label, 1, MAX_ID)


def price_field(data, key="price"):
    try:
        value = float(str(data.get(key)).replace(",", ".").strip())
    except ValueError:
        raise ApiError("El precio debe ser un número, por ejemplo 12.50.")
    if not math.isfinite(value) or not 0 <= value <= 10000:
        raise ApiError("El precio debe estar entre 0 y 10000.")
    return round(value, 2)


def choice_field(data, key, label, options):
    value = data.get(key)
    if value not in options:
        raise ApiError(f"{label} no es válido. Opciones: {', '.join(options)}.")
    return value


def parse_date(value):
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").date()
    except ValueError:
        raise ApiError("La fecha no es válida. Usa el formato AAAA-MM-DD.")


def parse_time(value):
    try:
        return datetime.strptime(str(value or ""), "%H:%M").time()
    except ValueError:
        raise ApiError("La hora no es válida. Usa el formato HH:MM.")
