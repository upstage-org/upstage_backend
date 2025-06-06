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

from typing import List, Optional
from ariadne import MutationType, QueryType, make_executable_schema
from global_config import authenticated, convert_keys_to_camel_case
from ariadne.asgi import GraphQL
from mails.helpers.mail import send
from studio_management.http.graphql import type_defs
from studio_management.http.validation import (
    BatchUserInput,
    ChangePasswordInput,
    UpdateUserInput,
)
from studio_management.services.studio import StudioService
from users.db_models.user import ADMIN, ROLES, SUPER_ADMIN, PLAYER, UserModel


query = QueryType()
mutation = MutationType()


@query.field("whoami")
@authenticated()
def current_user(_, info):
    user = info.context["request"].state.current_user
    return convert_keys_to_camel_case({**user, "roleName": ROLES[int(user["role"])]})


@query.field("adminPlayers")
@authenticated()
def admin_players(_, __, **kwargs):
    return StudioService().admin_players(kwargs)


@query.field("getAllStages")
@authenticated()
def stages(_, info):
    return StudioService().stages(UserModel(**info.context["request"].state.current_user))


@query.field("users")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def users(_, __, active: bool = True):
    return StudioService().get_users(active)


@mutation.field("batchUserCreation")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def create_users(_, __, users: List[BatchUserInput]):
    return StudioService().create_users(users)


@mutation.field("updateUser")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def update_user(_, __, input: UpdateUserInput, studio_service=StudioService()):
    return await studio_service.update_user(UpdateUserInput(**input))


@mutation.field("deleteUser")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def delete_user(_, info, id: int):
    return StudioService().delete_user(
        id, UserModel(**info.context["request"].state.current_user)
    )


@mutation.field("sendEmail")
@authenticated()
async def send_email(_, __, input):
    await send(
        input["recipients"].split(","),
        input["subject"],
        input["body"],
        input["bcc"].split(",") if input["bcc"] else [],
    )
    return {"success": True}


@mutation.field("changePassword")
@authenticated()
def change_password(_, __, input: ChangePasswordInput):
    return StudioService().change_password(ChangePasswordInput(**input))


@mutation.field("calcSizes")
def calc_sizes(_, __):
    return StudioService().calc_sizes()


@mutation.field("requestPermission")
@authenticated()
def request_permission(_, info, assetId: int, note: Optional[str] = None):
    return StudioService().request_permission(
        UserModel(**info.context["request"].state.current_user), assetId, note
    )


@mutation.field("confirmPermission")
@authenticated()
async def confirm_permission(_, info, id: int, approved: Optional[bool] = False):
    return await StudioService().confirm_permission(
        UserModel(**info.context["request"].state.current_user), id, approved
    )


@mutation.field("quickAssignMutation")
@authenticated()
def quick_assign_mutation(_, info, stageIds: list[int], assetId: int):
    return StudioService().quick_assign_mutation(
        UserModel(**info.context["request"].state.current_user), stageIds, assetId
    )


schema = make_executable_schema(type_defs, query, mutation)
studio_graphql_app = GraphQL(schema, debug=True)
