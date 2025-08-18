# -*- coding: iso8859-15 -*-
from datetime import datetime
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

from global_config.env import CLIENT_MAX_BODY_SIZE

from global_config.helpers.object import convert_keys_to_camel_case
from global_config.database import ScopedSession, DBSession
from mails.helpers.mail import send
from upstage_options.db_models.config import ConfigModel
from upstage_options.http.validation import ConfigInput, SystemEmailInput

TERMS_OF_SERVICE = "TERMS_OF_SERVICE"
MANUAL = "MANUAL"
EMAIL_SUBJECT_PREFIX = "EMAIL_SUBJECT_PREFIX"
ENABLE_DONATE = "ENABLE_DONATE"
FOYER_TITLE = "FOYER_TITLE"
FOYER_DESCRIPTION = "FOYER_DESCRIPTION"
FOYER_MENU = "FOYER_MENU"
SHOW_REGISTRATION = "SHOW_REGISTRATION"
EMAIL_SIGNATURE = "EMAIL_SIGNATURE"
ADDING_EMAIL_SIGNATURE = "ADDING_EMAIL_SIGNATURE"


class SettingService:
    def get_config(self, name: str, session=DBSession):
        return session.query(ConfigModel).filter_by(name=name).first()

    def upload_limit(self):
        """
        In the future this will be 0 in nginx, and value for
        code will be in the database. The code itself will enforce
        the limit.
        """
        return {"limit": CLIENT_MAX_BODY_SIZE}

    def system_info(self):
        enable_donate = self.get_config(ENABLE_DONATE)
        addingEmailSignature = self.get_config(ADDING_EMAIL_SIGNATURE)

        addingEmailSignature = (
            addingEmailSignature.to_dict()
            if addingEmailSignature
            else {"id": 1, "name": "ADDING_EMAIL_SIGNATURE", "value": "true"}
        )

        return convert_keys_to_camel_case(
            {
                "termsOfService": self.get_config(TERMS_OF_SERVICE),
                "manual": self.get_config(MANUAL),
                "esp": self.get_config(EMAIL_SUBJECT_PREFIX),
                "enableDonate": {
                    **enable_donate.to_dict(),
                    "value": enable_donate.value == "true",
                },
                "emailSignature": self.get_config(EMAIL_SIGNATURE),
                "addingEmailSignature": {
                    **addingEmailSignature,
                    "value": addingEmailSignature["value"] == "true",
                },
            }
        )

    def foyer_info(self):
        show_registration = self.get_config(SHOW_REGISTRATION)

        return convert_keys_to_camel_case(
            {
                "title": self.get_config(FOYER_TITLE),
                "description": self.get_config(FOYER_DESCRIPTION),
                "menu": self.get_config(FOYER_MENU),
                "showRegistration": {
                    **show_registration.to_dict(),
                    "value": show_registration.value == "true",
                },
            }
        )

    def update_terms_of_service(self, url: str):
        with ScopedSession() as local_db_session:
            config = self.get_config(TERMS_OF_SERVICE, local_db_session)
            if not config:
                config = ConfigModel(name=TERMS_OF_SERVICE, value=url)
                local_db_session.add(config)
            else:
                config.value = url
            local_db_session.flush()
        config = self.get_config(TERMS_OF_SERVICE)
        return convert_keys_to_camel_case(config.to_dict())

    def save_config(self, input: ConfigInput):
        with ScopedSession() as local_db_session:
            config = self.get_config(input.name, local_db_session)
            if not config:
                config = ConfigModel(name=input.name, value=input.value)
                local_db_session.add(config)
            else:
                if input.name == ENABLE_DONATE or input.name == SHOW_REGISTRATION:
                    config.value = "true" if input.enabled else "false"
                else:
                    config.value = input.value

            local_db_session.flush()

        config = self.get_config(input.name)
        return convert_keys_to_camel_case(config)

    async def send_email(self, input: SystemEmailInput):
        await send(
            input.recipients.split(","),
            input.subject,
            input.body,
            input.bcc.split(",") if input.bcc else [],
        )
        return {"success": True}
