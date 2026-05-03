# -*- coding: iso8859-15 -*-
import os
import sys

from typing import List, Optional

from ariadne import MutationType, QueryType, make_executable_schema
from graphql import GraphQLError

from upstage_backend.global_config import logger
from upstage_backend.global_config.decorators.authenticated import authenticated
from upstage_backend.global_config.env import EMAIL_HOST
from upstage_backend.global_config.helpers.object import convert_keys_to_camel_case
from ariadne.asgi import GraphQL
from upstage_backend.mails.helpers.mail import send
from upstage_backend.studio_management.http.graphql import type_defs
from upstage_backend.studio_management.http.validation import (
    BatchUserInput,
    ChangePasswordInput,
    UpdateUserInput,
)
from upstage_backend.studio_management.services.studio import StudioService
from upstage_backend.users.db_models.user import ADMIN, ROLES, SUPER_ADMIN, PLAYER, UserModel


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


def _split_email_list(raw: Optional[str]) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    return [p.strip() for p in str(raw).split(",") if p.strip()]


@mutation.field("sendEmail")
@authenticated()
async def send_email(_, info, input):
    """
    Send email to arbitrary recipients using this server's SMTP (studio UI).
    Not related to the removed cross-server mail relay.
    """
    if not EMAIL_HOST:
        raise GraphQLError(
            "Email is not configured on this server (set EMAIL_HOST and related vars)."
        )

    user = info.context["request"].state.current_user
    role = int(user["role"])

    if role not in (SUPER_ADMIN, ADMIN) and not user.get("can_send_email"):
        raise GraphQLError(
            "You do not have permission to send email from the studio."
        )

    to_list = _split_email_list(input.get("recipients"))
    if not to_list:
        raise GraphQLError("At least one recipient is required.")

    try:
        await send(
            to_list,
            input["subject"],
            input["body"],
            _split_email_list(input.get("bcc")),
        )
    except Exception:
        logger.exception("Studio sendEmail: SMTP send failed")
        raise GraphQLError(
            "Failed to send email. Check SMTP configuration (EMAIL_HOST, EMAIL_PORT, TLS, credentials)."
        ) from None
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
