"""create broker profiles table

Revision ID: 002_create_broker_profiles
Revises: 001_create_message_logs
Create Date: 2026-06-11 20:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_create_broker_profiles"
down_revision: Union[str, None] = "001_create_message_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broker_profiles",
        sa.Column("instance_id", sa.String(), nullable=False),
        sa.Column("broker_name", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=False),
        sa.Column("site_base_url", sa.String(), nullable=False),
        sa.Column("bot_name", sa.String(), nullable=False, server_default="Ana"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("instance_id"),
    )
    op.create_index(op.f("ix_broker_profiles_instance_id"), "broker_profiles", ["instance_id"], unique=False)
    op.create_index(op.f("ix_broker_profiles_created_at"), "broker_profiles", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_broker_profiles_created_at"), table_name="broker_profiles")
    op.drop_index(op.f("ix_broker_profiles_instance_id"), table_name="broker_profiles")
    op.drop_table("broker_profiles")
