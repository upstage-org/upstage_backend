# -*- coding: iso8859-15 -*-
import os
import sys

from functools import wraps
from fastapi import Request
import jwt
from graphql import GraphQLError
from upstage_backend.global_config.env import ALGORITHM, SECRET_KEY
from upstage_backend.global_config.helpers.bearer import parse_bearer_token
from upstage_backend.users.services.user import UserService


def authenticated(allowed_roles=None):
    if allowed_roles is None:
        allowed_roles = []

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from upstage_backend.authentication.services.auth import AuthenticationService

            info = args[1]
            request: Request = info.context["request"]
            authorization: str = request.headers.get("Authorization")
            token = parse_bearer_token(authorization)
            if not token:
                raise GraphQLError("Authenticated Failed")

            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("user_id")
                session = AuthenticationService().get_session(token, user_id)

                if not session:
                    raise GraphQLError("Authenticated Failed")

                current_user = UserService().find_by_id(user_id)

                if not current_user:
                    raise GraphQLError("Authenticated Failed")

                if allowed_roles and current_user.role not in allowed_roles:
                    raise GraphQLError("Permission denied")

                request.state.current_user = current_user.to_dict()

            except jwt.ExpiredSignatureError:
                raise GraphQLError("Signature has expired")
            except jwt.InvalidTokenError:
                raise GraphQLError("Authenticated Failed")

            return func(*args, **kwargs)

        return wrapper

    return decorator
