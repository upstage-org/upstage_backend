from ariadne import MutationType, QueryType
from graphql import GraphQLError
from pydantic import ValidationError
from upstage_backend.global_config.helpers.object import convert_keys_to_camel_case
from upstage_backend.global_config.decorators.authenticated import authenticated

from upstage_backend.users.http.validation import (
    CreateUserInput,
    PasswordResetTokenInput,
    ResetPasswordInput,
    format_validation_error,
)
from upstage_backend.users.services.upload_limit import effective_upload_limit
from upstage_backend.users.services.user import UserService

query = QueryType()
mutation = MutationType()


@query.field("currentUser")
@authenticated()
def current_user(_, info):
    user = info.context["request"].state.current_user
    return convert_keys_to_camel_case(
        {
            **user,
            "effectiveUploadLimit": effective_upload_limit(user["role"], user.get("upload_limit")),
        }
    )


@mutation.field("createUser")
def create_user(_, info, inbound: dict):
    try:
        validated = CreateUserInput(**inbound)
    except ValidationError as exc:
        raise GraphQLError(format_validation_error(exc)) from exc
    return UserService().create(validated.model_dump(), info.context["request"])


@mutation.field("requestPasswordReset")
async def request_password_reset(_, info, email):
    return await UserService().request_password_reset(email)


@mutation.field("verifyPasswordReset")
async def verify_password_reset(_, info, input):
    try:
        validated = PasswordResetTokenInput(**input)
    except ValidationError as exc:
        raise GraphQLError(format_validation_error(exc)) from exc
    return await UserService().verify_password_reset(validated)


@mutation.field("resetPassword")
async def reset_password(_, info, input):
    try:
        validated = ResetPasswordInput(**input)
    except ValidationError as exc:
        raise GraphQLError(format_validation_error(exc)) from exc
    return await UserService().reset_password(validated)
