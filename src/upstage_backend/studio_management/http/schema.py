from typing import List, Optional

from ariadne import MutationType, QueryType
from graphql import GraphQLError

from upstage_backend.global_config import logger
from upstage_backend.global_config.decorators.authenticated import authenticated
from upstage_backend.global_config.env import EMAIL_HOST
from upstage_backend.global_config.helpers.bearer import parse_bearer_token
from upstage_backend.global_config.helpers.object import convert_keys_to_camel_case
from upstage_backend.mails.helpers.mail import send
from upstage_backend.studio_management.http.validation import (
    BatchUserInput,
    ChangePasswordInput,
    UpdateUserInput,
)
from upstage_backend.studio_management.services.studio import StudioService
from upstage_backend.users.services.upload_limit import effective_upload_limit
from upstage_backend.users.db_models.user import (
    ADMIN,
    ROLES,
    SUPER_ADMIN,
    PLAYER,
)
from upstage_backend.global_config.helpers.context import current_user


query = QueryType()
mutation = MutationType()


@query.field("whoami")
@authenticated()
def resolve_whoami(_, info):
    user = info.context["request"].state.current_user
    return convert_keys_to_camel_case(
        {
            **user,
            "roleName": ROLES[int(user["role"])],
            "effectiveUploadLimit": effective_upload_limit(user["role"], user.get("upload_limit")),
        }
    )


@query.field("adminPlayers")
@authenticated()
def admin_players(_, info, **kwargs):
    # Players use this list too (media permissions / stage filters), so the
    # service trims non-admin callers to UserModel.PUBLIC_FIELDS.
    return StudioService().admin_players(kwargs, info.context["request"].state.current_user)


@query.field("getAllStages")
@authenticated()
def stages(_, info):
    return StudioService().stages(current_user(info))


@query.field("users")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def users(_, info, active: bool = True):
    # Player screens (stage filter, media permissions) list other players by
    # id / username / display name; the service trims non-admin callers to
    # UserModel.PUBLIC_FIELDS so e-mail and the rest stay admin-only.
    return StudioService().get_users(active, info.context["request"].state.current_user)


@mutation.field("batchUserCreation")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def create_users(_, __, users: List[BatchUserInput]):
    return StudioService().create_users(users)


@mutation.field("updateUser")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
async def update_user(_, info, input: UpdateUserInput):
    return await StudioService().update_user(
        UpdateUserInput(**input), info.context["request"].state.current_user
    )


@mutation.field("deleteUser")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def delete_user(_, info, id: int, contentAction: str = "REASSIGN_TO_ADMIN"):
    return StudioService().delete_user(
        id,
        current_user(info),
        contentAction,
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
        raise GraphQLError("You do not have permission to send email from the studio.")

    to_list = _split_email_list(input.get("recipients"))
    bcc_list = _split_email_list(input.get("bcc"))
    # All-BCC sends are valid: the UI defaults recipients to BCC, and
    # create_email always puts EMAIL_HOST_FROM in the To header.
    if not to_list and not bcc_list:
        raise GraphQLError("At least one recipient is required.")

    try:
        await send(
            to_list,
            input["subject"],
            input["body"],
            bcc_list,
            honor_to=True,
        )
    except Exception:
        logger.exception("Studio sendEmail: SMTP send failed")
        raise GraphQLError(
            "Failed to send email. Check SMTP configuration (EMAIL_HOST, EMAIL_PORT, TLS, credentials)."
        ) from None
    return {"success": True}


@mutation.field("changePassword")
@authenticated()
def change_password(_, info, input: ChangePasswordInput):
    request = info.context["request"]
    return StudioService().change_password(
        ChangePasswordInput(**input),
        request.state.current_user,
        keep_access_token=parse_bearer_token(request.headers.get("Authorization")),
    )


@mutation.field("calcSizes")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN])
def calc_sizes(_, __):
    return StudioService().calc_sizes()


@mutation.field("requestPermission")
@authenticated()
def request_permission(_, info, assetId: int, note: Optional[str] = None):
    return StudioService().request_permission(
        current_user(info), assetId, note
    )


@mutation.field("confirmPermission")
@authenticated()
async def confirm_permission(_, info, id: int, approved: Optional[bool] = False):
    return await StudioService().confirm_permission(
        current_user(info), id, approved
    )


@mutation.field("dismissNotification")
@authenticated(allowed_roles=[SUPER_ADMIN, ADMIN, PLAYER])
def dismiss_notification(_, info, id: int):
    return StudioService().dismiss_notification(
        current_user(info), id
    )


@mutation.field("quickAssignMutation")
@authenticated()
def quick_assign_mutation(_, info, stageIds: list[int], assetId: int):
    return StudioService().quick_assign_mutation(
        current_user(info), stageIds, assetId
    )
