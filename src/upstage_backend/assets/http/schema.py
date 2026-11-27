from ariadne import MutationType, QueryType
from upstage_backend.assets.http.validation import (
    MediaTableInput,
    SaveMediaInput,
    UpdateMediaStatusInput,
)
from upstage_backend.global_config.decorators.authenticated import authenticated
from upstage_backend.assets.services.asset import AssetService
from upstage_backend.users.db_models.user import ADMIN, PLAYER, SUPER_ADMIN
from upstage_backend.global_config.helpers.context import current_user

query = QueryType()
mutation = MutationType()


@query.field("mediaList")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def media_list(_, info, **kwargs):
    return AssetService().get_all_medias(
        current_user(info), kwargs
    )


@query.field("media")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def search_assets(_, info, **kwargs):
    return AssetService().search_assets(
        current_user(info),
        MediaTableInput(**kwargs["input"]),
    )


@query.field("mediaTypes")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def get_media_types(_, __):
    return AssetService().get_media_types()


@query.field("tags")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def get_tags(_, __):
    return AssetService().get_tags()


@query.field("voices")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def get_voices(_, __):
    return AssetService().get_voices()


@mutation.field("uploadFile")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def upload_file(_, info, base64: str, filename: str):
    return await AssetService().upload_file_async(
        current_user(info), base64, filename
    )


@mutation.field("saveMedia")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def save_media(_, info, input: SaveMediaInput):
    return AssetService().save_media(
        current_user(info),
        SaveMediaInput(**input),
    )


@mutation.field("deleteMedia")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def delete_media(_, info, id: int):
    return AssetService().delete_media(current_user(info), id)


@mutation.field("updateMediaStatus")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def update_status(_, info, input: UpdateMediaStatusInput):
    return AssetService().update_status(
        current_user(info),
        UpdateMediaStatusInput(**input),
    )
