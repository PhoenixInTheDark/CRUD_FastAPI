"""initial

Revision ID: 6542b928856d
Revises: 
Create Date: 2026-02-27 15:57:57.187581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6542b928856d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nickname", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nickname"),
    )
    op.create_index(
        op.f("ix_contacts_nickname"),
        "contacts",
        ["nickname"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_contacts_nickname"), table_name="contacts")
    op.drop_table("contacts")
