# -*- coding: iso8859-15 -*-
import os
import sys

from secrets import token_urlsafe

from graphql import GraphQLError
from upstage_backend.global_config import get_session
from upstage_backend.global_config.helpers.object import convert_keys_to_camel_case
from upstage_backend.licenses.http.validation import LicenseInput
from upstage_backend.assets.db_models.asset_license import AssetLicenseModel


class LicenseService:
    def __init__(self):
        pass

    def create_license(self, license_input: LicenseInput):
        session = get_session()
        asset_path = token_urlsafe(16)

        license = AssetLicenseModel(
            asset_id=license_input.assetId,
            level=license_input.level,
            permissions=license_input.permissions,
        )
        session.add(license)
        session.flush()
        license = (
            session.query(AssetLicenseModel).filter_by(id=license.id).first()
        )

        return {
            **convert_keys_to_camel_case(license.to_dict()),
            "assetPath": asset_path,
        }

    def get_license(self, l_id, session=None):
        if session is None:
            session = get_session()
        return session.query(AssetLicenseModel).filter_by(id=l_id).first()

    async def revoke_license(self, license_id: int):
        session = get_session()
        try:
            license = self.get_license(license_id, session=session)

            if license is None:
                raise GraphQLError("License not found")

            session.delete(license)
            return "License revoked {}".format(license_id)
        except GraphQLError:
            raise
        except Exception:
            return "Failed to revoke license {}".format(license_id)
