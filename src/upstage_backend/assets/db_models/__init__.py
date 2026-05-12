# -*- coding: iso8859-15 -*-
"""
Asset-domain ORM models.

Importing this package eagerly registers every asset model class on
``Base.registry``. This matters because ``AssetModel`` uses string class
names in its ``relationship(...)`` declarations (e.g. ``"AssetLicenseModel"``,
``"MediaTagModel"``) which SQLAlchemy resolves at mapper-configuration time,
i.e. on the first ``session.query(...)``. Any standalone entry point
(scripts, workers, ad-hoc jobs) that only imports a subset of the asset
models risks hitting ``InvalidRequestError: failed to locate a name
('AssetLicenseModel')`` when the mapper tries to resolve those strings.

Importing ``upstage_backend.assets.db_models`` (or any single symbol from
it via ``from ... import X``) is enough to make all asset models present
in the registry, because Python executes this ``__init__`` once and that
load triggers the per-module imports below.
"""

from upstage_backend.assets.db_models.asset import AssetModel
from upstage_backend.assets.db_models.asset_attribute import AssetAttributeModel
from upstage_backend.assets.db_models.asset_license import AssetLicenseModel
from upstage_backend.assets.db_models.asset_type import AssetTypeModel
from upstage_backend.assets.db_models.asset_usage import AssetUsageModel
from upstage_backend.assets.db_models.media_tag import MediaTagModel
from upstage_backend.assets.db_models.tag import TagModel

__all__ = [
    "AssetModel",
    "AssetAttributeModel",
    "AssetLicenseModel",
    "AssetTypeModel",
    "AssetUsageModel",
    "MediaTagModel",
    "TagModel",
]
