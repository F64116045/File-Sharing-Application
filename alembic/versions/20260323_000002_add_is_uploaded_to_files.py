"""add is_uploaded status to files

Revision ID: 20260323_000002
Revises: 20260323_000001
Create Date: 2026-03-23 01:20:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260323_000002"
down_revision: Union[str, Sequence[str], None] = "20260323_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column("is_uploaded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("files", "is_uploaded")
