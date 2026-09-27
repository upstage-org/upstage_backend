"""
Request-context helpers for GraphQL resolvers.

`@authenticated` stores the caller as a plain dict on `request.state`
(so it survives the ASGI boundary); resolvers used to rebuild the model
inline, `UserModel(**info.context["request"].state.current_user)`, at 35
call sites. One helper keeps that shape in a single place.
"""

from upstage_backend.users.db_models.user import UserModel


def current_user(info) -> UserModel:
    """The authenticated caller for this resolver, as a (detached) UserModel."""
    return UserModel(**info.context["request"].state.current_user)
