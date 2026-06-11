"""create message logs table

Revision ID: 001_create_message_logs
Revises:
Create Date: 2026-06-11 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_create_message_logs"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("phone", sa.String(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("step", sa.String(), nullable=False),
        sa.Column("intent", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_message_logs_id"), "message_logs", ["id"], unique=False)
    op.create_index(op.f("ix_message_logs_phone"), "message_logs", ["phone"], unique=False)
    op.create_index(op.f("ix_message_logs_created_at"), "message_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_message_logs_created_at"), table_name="message_logs")
    op.drop_index(op.f("ix_message_logs_phone"), table_name="message_logs")
    op.drop_index(op.f("ix_message_logs_id"), table_name="message_logs")
    op.drop_table("message_logs")
