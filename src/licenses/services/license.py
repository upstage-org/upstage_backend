# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

from secrets import token_urlsafe

from graphql import GraphQLError
from global_config.database import ScopedSession, DBSession
from global_config.helpers.object import convert_keys_to_camel_case
from licenses.http.validation import LicenseInput
from assets.db_models.asset_license import AssetLicenseModel


class LicenseService:
    def __init__(self):
        pass

    def create_license(self, license_input: LicenseInput):
        with ScopedSession() as session:
            asset_path = token_urlsafe(16)

            license = AssetLicenseModel(
                asset_id=license_input.assetId,
                level=license_input.level,
                permissions=license_input.permissions,
            )
            session.add(license)
            session.commit()
            session.flush()
            license = (
                DBSession.query(AssetLicenseModel).filter_by(id=license.id).first()
            )

            return {
                **convert_keys_to_camel_case(license.to_dict()),
                "assetPath": asset_path,
            }

    def get_license(self, l_id, session=DBSession):
        return session.query(AssetLicenseModel).filter_by(id=l_id).first()

    async def revoke_license(self, license_id: int):
        with ScopedSession() as session:
            try:
                license = self.get_license(license_id, session=session)

                if license is None:
                    raise GraphQLError("License not found")

                session.delete(license)
                session.commit()
                return "License revoked {}".format(license_id)
            except Exception as e:
                return "Failed to revoke license {}".format(license_id)
            finally:
                session.close()
