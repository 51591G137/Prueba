"""Pequeñas utilidades: fechas en UTC e importes en euros sin errores de redondeo."""
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal


def utcnow():
    return datetime.now(timezone.utc)


def iso_utc(moment):
    """Fecha y hora en ISO 8601 con 'Z' al final (UTC). La app la convierte a la hora local del móvil."""
    if moment is None:
        return None
    if moment.tzinfo is None:  # SQLite devuelve fechas sin zona horaria
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def money(value):
    """Convierte a Decimal con 2 decimales (se calcula con Decimal y solo se devuelve float al final)."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def line_total(unit_price, quantity):
    return money(money(unit_price) * quantity)
