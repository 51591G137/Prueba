"""Registro de todos los módulos. Para añadir uno nuevo: crea su routes.py y añádelo aquí."""


def register_blueprints(app):
    from .billing.routes import bp as billing
    from .customers.routes import bp as customers
    from .menu.routes import bp as menu
    from .orders.routes import bp as orders
    from .pages import bp as pages
    from .payments.routes import bp as payments
    from .reservations.routes import bp as reservations
    from .restaurants.routes import bp as restaurants
    from .tables.routes import bp as tables
    from .users.routes import bp as users

    for blueprint in (pages, users, customers, restaurants, tables, menu, payments, orders, billing, reservations):
        app.register_blueprint(blueprint)
