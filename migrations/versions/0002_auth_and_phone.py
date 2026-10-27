"""auth_and_phone

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phone', sa.String(length=30), nullable=True))
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=80),
               nullable=True)
        batch_op.create_index(batch_op.f('ix_customers_phone'), ['phone'], unique=True)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('password_hash')

    with op.batch_alter_table('customers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_customers_phone'))
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=80),
               nullable=False)
        batch_op.drop_column('phone')
