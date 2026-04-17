"""Merge the worker claim-token and secure-default schema heads.

Revision ID: 009_merge_ci_heads
Revises: 008_user_admin_bootstrap, 006_job_claim_token
Create Date: 2026-04-17

"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "009_merge_ci_heads"
down_revision: Union[tuple[str, str], None] = ("008_user_admin_bootstrap", "006_job_claim_token")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
