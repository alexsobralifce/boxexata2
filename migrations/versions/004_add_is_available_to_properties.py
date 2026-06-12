"""add is_available to properties table

Revision ID: 004_add_is_available_to_properties
Revises: 003_create_properties
Create Date: 2026-06-12 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004_add_is_available_to_properties"
down_revision: Union[str, None] = "003_create_properties"


def upgrade() -> None:
    op.add_column(
        "properties",
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("properties", "is_available")
