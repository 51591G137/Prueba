"""esquema inicial (versión 2)

Crea todas las tablas. Si la base de datos trae restos de versiones anteriores (solo datos de
prueba), se eliminan antes: es lo único destructivo que hace esta migración. Se borran las tablas
con nombres de esta app (las de la versión 1 y las nuevas) y las que dependen de ellas por clave
foránea; cualquier otra tabla de la base de datos no se toca.
Las migraciones siguientes ya no borrarán datos.

Revision ID: 0001
Revises:
Create Date: 2026-10-23
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

# Tablas que son de esta app: las de la versión 1 y las que crea esta migración.
# Antes de ejecutarse la 0001 no debería existir ninguna con estos nombres, salvo restos antiguos.
APP_TABLES = {
    "users", "customers", "restaurants", "tables", "menu_items", "reservations",  # versión 1
    "users_restaurants", "items", "payment_methods", "orders", "orders_item", "bills",  # esta versión
}


def drop_legacy_schema():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    doomed = existing & APP_TABLES
    if not doomed:
        return

    # También las tablas que dependen de las anteriores por clave foránea, de forma transitiva
    # (por ejemplo un antiguo order_items que apunta a menu_items).
    grew = True
    while grew:
        grew = False
        for name in sorted(existing - doomed):
            if any(fk["referred_table"] in doomed for fk in inspector.get_foreign_keys(name)):
                doomed.add(name)
                grew = True

    if bind.dialect.name == "postgresql":
        quote = bind.dialect.identifier_preparer.quote
        for name in sorted(doomed):
            op.execute(f"DROP TABLE IF EXISTS {quote(name)} CASCADE")
        return

    # SQLite y otras: no hay CASCADE, así que primero se borran las tablas que dependen de otras.
    remaining = set(doomed)
    while remaining:
        free = [
            name for name in sorted(remaining)
            if not any(fk["referred_table"] == name for other in remaining - {name} for fk in inspector.get_foreign_keys(other))
        ]
        for name in free or sorted(remaining):  # si hubiera un ciclo, se intenta igualmente
            op.drop_table(name)
            remaining.discard(name)


def upgrade():
    drop_legacy_schema()
    op.create_table('customers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_customers'))
    )
    op.create_table('restaurants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('address', sa.String(length=200), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_restaurants'))
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_table('items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('restaurant_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.String(length=300), nullable=True),
    sa.Column('price', sa.Numeric(precision=10, scale=2, asdecimal=False), nullable=False),
    sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], name=op.f('fk_items_restaurant_id_restaurants'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_items'))
    )
    with op.batch_alter_table('items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_items_restaurant_id'), ['restaurant_id'], unique=False)

    op.create_table('payment_methods',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('restaurant_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=60), nullable=False),
    sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], name=op.f('fk_payment_methods_restaurant_id_restaurants'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payment_methods')),
    sa.UniqueConstraint('restaurant_id', 'name', name='uq_payment_methods_name')
    )
    with op.batch_alter_table('payment_methods', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_payment_methods_restaurant_id'), ['restaurant_id'], unique=False)

    op.create_table('tables',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('restaurant_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=40), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], name=op.f('fk_tables_restaurant_id_restaurants'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tables'))
    )
    with op.batch_alter_table('tables', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tables_restaurant_id'), ['restaurant_id'], unique=False)

    op.create_table('users_restaurants',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('restaurant_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], name=op.f('fk_users_restaurants_restaurant_id_restaurants'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_users_restaurants_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users_restaurants')),
    sa.UniqueConstraint('user_id', 'restaurant_id', name='uq_users_restaurants_pair')
    )
    with op.batch_alter_table('users_restaurants', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_restaurants_restaurant_id'), ['restaurant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_restaurants_user_id'), ['user_id'], unique=False)

    op.create_table('bills',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('restaurant_id', sa.Integer(), nullable=False),
    sa.Column('table_id', sa.Integer(), nullable=True),
    sa.Column('table_name', sa.String(length=40), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('open_datetime', sa.DateTime(timezone=True), nullable=False),
    sa.Column('close_datetime', sa.DateTime(timezone=True), nullable=True),
    sa.Column('total', sa.Numeric(precision=10, scale=2, asdecimal=False), nullable=False),
    sa.Column('payment_method_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['payment_method_id'], ['payment_methods.id'], name=op.f('fk_bills_payment_method_id_payment_methods'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], name=op.f('fk_bills_restaurant_id_restaurants'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['table_id'], ['tables.id'], name=op.f('fk_bills_table_id_tables'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_bills_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bills'))
    )
    with op.batch_alter_table('bills', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bills_restaurant_id'), ['restaurant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_bills_table_id'), ['table_id'], unique=False)

    op.create_table('reservations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('table_id', sa.Integer(), nullable=False),
    sa.Column('customer_id', sa.Integer(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('time', sa.Time(), nullable=False),
    sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], name=op.f('fk_reservations_customer_id_customers'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['table_id'], ['tables.id'], name=op.f('fk_reservations_table_id_tables'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reservations')),
    sa.UniqueConstraint('table_id', 'date', 'time', name='uq_reservations_slot')
    )
    with op.batch_alter_table('reservations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reservations_customer_id'), ['customer_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_reservations_table_id'), ['table_id'], unique=False)

    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('restaurant_id', sa.Integer(), nullable=False),
    sa.Column('table_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('bill_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('requests', sa.String(length=300), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('is_paid', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['bill_id'], ['bills.id'], name=op.f('fk_orders_bill_id_bills'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], name=op.f('fk_orders_restaurant_id_restaurants'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['table_id'], ['tables.id'], name=op.f('fk_orders_table_id_tables'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_orders_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_orders'))
    )
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_orders_bill_id'), ['bill_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_orders_restaurant_id'), ['restaurant_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_orders_table_id'), ['table_id'], unique=False)

    op.create_table('orders_item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('item_name', sa.String(length=120), nullable=False),
    sa.Column('unit_price', sa.Numeric(precision=10, scale=2, asdecimal=False), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['items.id'], name=op.f('fk_orders_item_item_id_items'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_orders_item_order_id_orders'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_orders_item_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_orders_item'))
    )
    with op.batch_alter_table('orders_item', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_orders_item_item_id'), ['item_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_orders_item_order_id'), ['order_id'], unique=False)



def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders_item', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_orders_item_order_id'))
        batch_op.drop_index(batch_op.f('ix_orders_item_item_id'))

    op.drop_table('orders_item')
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_orders_table_id'))
        batch_op.drop_index(batch_op.f('ix_orders_restaurant_id'))
        batch_op.drop_index(batch_op.f('ix_orders_bill_id'))

    op.drop_table('orders')
    with op.batch_alter_table('reservations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reservations_table_id'))
        batch_op.drop_index(batch_op.f('ix_reservations_customer_id'))

    op.drop_table('reservations')
    with op.batch_alter_table('bills', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bills_table_id'))
        batch_op.drop_index(batch_op.f('ix_bills_restaurant_id'))

    op.drop_table('bills')
    with op.batch_alter_table('users_restaurants', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_restaurants_user_id'))
        batch_op.drop_index(batch_op.f('ix_users_restaurants_restaurant_id'))

    op.drop_table('users_restaurants')
    with op.batch_alter_table('tables', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tables_restaurant_id'))

    op.drop_table('tables')
    with op.batch_alter_table('payment_methods', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payment_methods_restaurant_id'))

    op.drop_table('payment_methods')
    with op.batch_alter_table('items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_items_restaurant_id'))

    op.drop_table('items')
    op.drop_table('users')
    op.drop_table('restaurants')
    op.drop_table('customers')
