"""create files and shares tables

Revision ID: 20260323_000001
Revises:
Create Date: 2026-03-23 00:50:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260323_000001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_files_object_key", "files", ["object_key"], unique=True)

    op.create_table(
        "shares",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shares_expires_at", "shares", ["expires_at"], unique=False)
    op.create_index("ix_shares_file_id", "shares", ["file_id"], unique=False)
    op.create_index("ix_shares_token_hash", "shares", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_shares_token_hash", table_name="shares")
    op.drop_index("ix_shares_file_id", table_name="shares")
    op.drop_index("ix_shares_expires_at", table_name="shares")
    op.drop_table("shares")

    op.drop_index("ix_files_object_key", table_name="files")
    op.drop_table("files")
