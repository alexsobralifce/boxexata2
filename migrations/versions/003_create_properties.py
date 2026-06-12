"""create properties table

Revision ID: 003_create_properties
Revises: 002_create_broker_profiles
Create Date: 2026-06-12 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_create_properties"
down_revision: Union[str, None] = "002_create_broker_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "properties",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("ref", sa.String(), nullable=False),
        sa.Column("property_type", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("neighborhood", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("fees", sa.Float(), nullable=True, server_default="0.0"),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("parking_spaces", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("photos", sa.String(), nullable=False, server_default="[]"),
        sa.Column("intent", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_properties_id"), "properties", ["id"], unique=False)
    op.create_index(op.f("ix_properties_ref"), "properties", ["ref"], unique=False)
    op.create_index(op.f("ix_properties_created_at"), "properties", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_properties_created_at"), table_name="properties")
    op.drop_index(op.f("ix_properties_ref"), table_name="properties")
    op.drop_index(op.f("ix_properties_id"), table_name="properties")
    op.drop_table("properties")
