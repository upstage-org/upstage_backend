from ariadne import MutationType, QueryType
from upstage_backend.authentication.http.validation import LoginInput
from upstage_backend.authentication.services.auth import AuthenticationService


query = QueryType()
mutation = MutationType()


@mutation.field("login")
async def login(_, info, payload: LoginInput):
    return await AuthenticationService().login(
        LoginInput(**payload), info.context["request"]
    )


@mutation.field("refreshToken")
async def refresh_token(_, info):
    return await AuthenticationService().refresh_token(
        info.context["request"],
    )


@mutation.field("logout")
async def resolve_logout(_, info):
    return await AuthenticationService().logout(info.context["request"])
