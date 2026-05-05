"""Point TERMS_OF_SERVICE at public T&Cs, not repo LICENSE

scaffold_base_media used to overwrite TERMS_OF_SERVICE with the GitHub
LICENSE raw URL. Fix any row that still has that value.

Revision ID: a09bc4e8f1d0
Revises: f6e7b37dc826
Create Date: 2026-05-05

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a09bc4e8f1d0"
down_revision: Union[str, None] = "f6e7b37dc826"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LICENSE_RAW = "https://raw.githubusercontent.com/upstage-org/upstage/main/LICENSE"
_TERMS_PAGE = "https://upstage.org.nz/?page_id=9622"


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE config
        SET value = '{_TERMS_PAGE}'
        WHERE name = 'TERMS_OF_SERVICE'
          AND value = '{_LICENSE_RAW}'
        """
    )


def downgrade() -> None:
    # One-way fix; do not restore the LICENSE URL (ambiguous if T&Cs were set legitimately).
    pass
