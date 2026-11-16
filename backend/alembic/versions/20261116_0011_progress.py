"""progress: target weight and wins at check-in

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-16 19:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

WINS = ("energy", "sleep", "stairs")


def upgrade() -> None:
    op.add_column("profiles", sa.Column("target_weight_kg", sa.Numeric(5, 1), nullable=True))
    for name in WINS:
        op.add_column("checkins", sa.Column(name, sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    for name in reversed(WINS):
        op.drop_column("checkins", name)
    op.drop_column("profiles", "target_weight_kg")
