"""Insert default system configuration

Revision ID: e5f8bc8043a5
Revises: 0baf970d7eb2
Create Date: 2025-03-13 13:32:29.317683

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


TERMS_OF_SERVICE = "TERMS_OF_SERVICE"
MANUAL = "MANUAL"
EMAIL_SUBJECT_PREFIX = "EMAIL_SUBJECT_PREFIX"
ENABLE_DONATE = "ENABLE_DONATE"
FOYER_TITLE = "FOYER_TITLE"
FOYER_DESCRIPTION = "FOYER_DESCRIPTION"
FOYER_MENU = "FOYER_MENU"
SHOW_REGISTRATION = "SHOW_REGISTRATION"


revision: str = 'e5f8bc8043a5'
down_revision: Union[str, None] = '0baf970d7eb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    config_table = sa.table(
        'config',
        sa.column('name', sa.String),
        sa.column('value', sa.Text),
    )

    config_defaults = {
        TERMS_OF_SERVICE: "https://upstage.org.nz/?page_id=9622",
        MANUAL: "https://docs.upstage.live/",
        EMAIL_SUBJECT_PREFIX: "[UpStage Live]",
        ENABLE_DONATE: json.dumps(False),
        FOYER_TITLE: "UpStage: the cyberformance platform",
        FOYER_DESCRIPTION: (
            '<h3 style="text-align: center;"><em>online venue for live performance and remote collaboration</em></h3>\n'
            '<p style="text-align: center;"><strong><a title="And now ... !" href="https://upstage.org.nz/?event=and-now" target="_blank" rel="noopener">'
            '<img src="https://upstage.org.nz/wp-content/uploads/2025/01/andnow2-1536x926.png" alt="And now ... !" width="600" height="362" /></a><!--And now ... " performances and presentation<br />'
            'Saturday 8th March 2025<br />18:00 CET (<a href="https://tinyurl.com/AndNow080325" target="_blank" rel="noopener">find your local time here</a>)'
            '</strong></p>\n'
            '<p style="text-align: center;">Visit <a title="UpStage.org.nz" href="http://upstage.org.nz" target="_blank" rel="noopener">upstage.org.nz</a> to find out more, sign up for news and walk throughs,<br />'
            'and support this independent open source artist-led project!</p>\n'
            '<p>--&gt;</p>--></strong></p>'
        ),
        FOYER_MENU: (
            "UpStage User Manual (https://docs.upstage.live/)\n"
            "UpStage Website (https://upstage.org.nz/)\n"
            "Customise Foyer (/admin/configuration) (8,32)\n"
            "More\n"
            "> Contact (https://upstage.org.nz/?page_id=5)\n"
            "> FAQs (https://upstage.org.nz/?page_id=115)"
        ),
        SHOW_REGISTRATION: json.dumps(True)
    }

    # Iterate over the defaults and insert each if it doesn't already exist.
    for key, value in config_defaults.items():
        exists = connection.execute(
            sa.select(config_table.c.name).where(config_table.c.name == key)
        ).fetchone()
        print(exists)
        if exists is None:
            connection.execute(
                config_table.insert().values(
                    name=key,
                    value=value
                )
            )



def downgrade() -> None:
    pass
