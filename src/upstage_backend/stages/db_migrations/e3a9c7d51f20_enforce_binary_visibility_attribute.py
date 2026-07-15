"""Enforce binary stage visibility attribute

updateStage used to stringify an omitted visibility input straight into
the attribute row: str(None) -> "none", a truthy string that survived the
missing-value guard and overwrote the stored setting — and anything other
than "true" reads as hidden, so config-only saves (the Customisation tab)
silently pulled stages out of the foyer. The service now skips the write
when visibility is not supplied; this revision repairs the rows already
clobbered (any non-binary value becomes an explicit "false") and adds a
CHECK constraint so the visibility attribute can only ever hold
"true"/"false" again.

The repo intentionally carries two parallel alembic heads (see
7f1a5c9e02ad); compose runs `upgrade heads`. This revision chains onto
the stages-side head b1e7a2d94c03 so head count stays at two.

Revision ID: e3a9c7d51f20
Revises: b1e7a2d94c03
Create Date: 2026-07-16 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e3a9c7d51f20"
down_revision: Union[str, None] = "b1e7a2d94c03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE stage_attribute SET description = 'false' "
        "WHERE name = 'visibility' "
        "AND (description IS NULL OR description NOT IN ('true', 'false'))"
    )
    op.create_check_constraint(
        "stage_attribute_visibility_binary",
        "stage_attribute",
        "name != 'visibility' OR description IN ('true', 'false')",
    )


def downgrade() -> None:
    # Data repair is intentionally not reversed: the pre-corruption values
    # are unrecoverable and "false" is the safe reading of the bad rows.
    op.drop_constraint("stage_attribute_visibility_binary", "stage_attribute", type_="check")
