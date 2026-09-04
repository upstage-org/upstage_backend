# -*- coding: iso8859-15 -*-

from ariadne import MutationType, QueryType, make_executable_schema
from graphql import GraphQLError
from pydantic import ValidationError
from upstage_backend.global_config.helpers.object import convert_keys_to_camel_case
from upstage_backend.global_config.decorators.authenticated import authenticated
from upstage_backend.studio_management.http.graphql import type_defs
from ariadne.asgi import GraphQL

from upstage_backend.users.http.validation import CreateUserInput, format_validation_error
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
def create_user(_, info, inbound: dict, user_service=UserService()):
    try:
        validated = CreateUserInput(**inbound)
    except ValidationError as exc:
        raise GraphQLError(format_validation_error(exc)) from exc
    return user_service.create(validated.model_dump(), info.context["request"])


@mutation.field("requestPasswordReset")
async def request_password_reset(_, info, email, user_service=UserService()):
    return await user_service.request_password_reset(email)


@mutation.field("verifyPasswordReset")
async def verify_password_reset(_, info, input, user_service=UserService()):
    return await user_service.verify_password_reset(input)


@mutation.field("resetPassword")
async def reset_password(_, info, input, user_service=UserService()):
    return await user_service.reset_password(input)


schema = make_executable_schema(type_defs, query, mutation)
user_graphql_app = GraphQL(schema, debug=True)
