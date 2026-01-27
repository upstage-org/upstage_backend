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
from global_config.database import ScopedSession
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
    def get_config(self, name: str, session=None):
        if session is None:
            with ScopedSession() as local_db_session:
                return local_db_session.query(ConfigModel).filter_by(name=name).first()
        return session.query(ConfigModel).filter_by(name=name).first()

    def upload_limit(self):
        """
        In the future this will be 0 in nginx, and value for
        code will be in the database. The code itself will enforce
        the limit.
        """
        return {"limit": CLIENT_MAX_BODY_SIZE}

    def system_info(self):
        with ScopedSession() as local_db_session:
            # Load all configs within the same session context
            terms_of_service = local_db_session.query(ConfigModel).filter_by(name=TERMS_OF_SERVICE).first()
            manual = local_db_session.query(ConfigModel).filter_by(name=MANUAL).first()
            esp = local_db_session.query(ConfigModel).filter_by(name=EMAIL_SUBJECT_PREFIX).first()
            enable_donate = local_db_session.query(ConfigModel).filter_by(name=ENABLE_DONATE).first()
            email_signature = local_db_session.query(ConfigModel).filter_by(name=EMAIL_SIGNATURE).first()
            addingEmailSignature = local_db_session.query(ConfigModel).filter_by(name=ADDING_EMAIL_SIGNATURE).first()

            # Convert to dicts while objects are still attached to session
            addingEmailSignature_dict = (
                addingEmailSignature.to_dict()
                if addingEmailSignature
                else {"id": 1, "name": "ADDING_EMAIL_SIGNATURE", "value": "true"}
            )

            enable_donate_dict = (
                enable_donate.to_dict() if enable_donate else None
            )

            enable_donate_result = None
            if enable_donate_dict:
                enable_donate_result = {
                    **enable_donate_dict,
                    "value": enable_donate_dict.get("value") == "true",
                }

            result = {
                "termsOfService": terms_of_service.to_dict() if terms_of_service else None,
                "manual": manual.to_dict() if manual else None,
                "esp": esp.to_dict() if esp else None,
                "enableDonate": enable_donate_result,
                "emailSignature": email_signature.to_dict() if email_signature else None,
                "addingEmailSignature": {
                    **addingEmailSignature_dict,
                    "value": addingEmailSignature_dict.get("value") == "true",
                },
            }

        return convert_keys_to_camel_case(result)

    def foyer_info(self):
        with ScopedSession() as local_db_session:
            # Load all configs within the same session context
            title = local_db_session.query(ConfigModel).filter_by(name=FOYER_TITLE).first()
            description = local_db_session.query(ConfigModel).filter_by(name=FOYER_DESCRIPTION).first()
            menu = local_db_session.query(ConfigModel).filter_by(name=FOYER_MENU).first()
            show_registration = local_db_session.query(ConfigModel).filter_by(name=SHOW_REGISTRATION).first()

            # Convert to dicts while objects are still attached to session
            show_registration_dict = (
                show_registration.to_dict() if show_registration else None
            )

            show_registration_result = None
            if show_registration_dict:
                show_registration_result = {
                    **show_registration_dict,
                    "value": show_registration_dict.get("value") == "true",
                }

            result = {
                "title": title.to_dict() if title else None,
                "description": description.to_dict() if description else None,
                "menu": menu.to_dict() if menu else None,
                "showRegistration": show_registration_result,
            }

        return convert_keys_to_camel_case(result)

    def update_terms_of_service(self, url: str):
        with ScopedSession() as local_db_session:
            config = self.get_config(TERMS_OF_SERVICE, local_db_session)
            if not config:
                config = ConfigModel(name=TERMS_OF_SERVICE, value=url)
                local_db_session.add(config)
            else:
                config.value = url
            local_db_session.flush()
            # Convert to dict while object is still attached to session
            config_dict = config.to_dict()
        return convert_keys_to_camel_case(config_dict)

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
            # Convert to dict while object is still attached to session
            config_dict = config.to_dict()

        return convert_keys_to_camel_case(config_dict)

    async def send_email(self, input: SystemEmailInput):
        await send(
            input.recipients.split(","),
            input.subject,
            input.body,
            input.bcc.split(",") if input.bcc else [],
        )
        return {"success": True}
