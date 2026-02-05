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

import arrow
from datetime import timedelta
from global_config.helpers.object import get_naive_utc_now
from functools import wraps
from fastapi import Request
import jwt
from graphql import GraphQLError
from global_config.env import ALGORITHM, SECRET_KEY
from users.services.user import UserService

# When validating the access token, update latest_activity at most this often per user
# so the Player Management "Latest activity" column reflects recent activity.
LATEST_ACTIVITY_UPDATE_THROTTLE = timedelta(hours=1)


def authenticated(allowed_roles=None):
    if allowed_roles is None:
        allowed_roles = []

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from authentication.services.auth import AuthenticationService

            info = args[1]
            request: Request = info.context["request"]
            authorization: str = request.headers.get("Authorization")
            if not authorization:
                raise GraphQLError("Authenticated Failed")

            token = authorization.split(" ")[1]
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("user_id")
                session = AuthenticationService().get_session(token, user_id)

                if not session:
                    raise GraphQLError("Authenticated Failed")

                # Load user and convert to dict within session context
                from global_config.database import ScopedSession
                from users.db_models.user import UserModel
                
                with ScopedSession() as local_db_session:
                    current_user = (
                        local_db_session.query(UserModel)
                        .filter(UserModel.id == user_id, UserModel.active.is_(True))
                        .first()
                    )
                    
                    if not current_user:
                        raise GraphQLError("Authenticated Failed")

                    if allowed_roles and current_user.role not in allowed_roles:
                        raise GraphQLError("Permission denied")

                    # Keep "Latest activity" in Player Management accurate: update when we see
                    # an authenticated request, throttled to avoid a write on every request.
                    # Use timezone-unaware UTC-0 datetime
                    now = get_naive_utc_now()
                    latest_activity = current_user.latest_activity
                    # Convert timezone-aware datetime to timezone-unaware UTC if needed
                    if latest_activity is not None:
                        if latest_activity.tzinfo is not None:
                            # Convert to UTC, then remove timezone info to get naive UTC
                            latest_activity_naive = arrow.get(latest_activity).to('UTC').datetime.replace(tzinfo=None)
                        else:
                            # Already timezone-naive, use as-is
                            latest_activity_naive = latest_activity
                    else:
                        latest_activity_naive = None
                    if (
                        latest_activity_naive is None
                        or (now - latest_activity_naive) > LATEST_ACTIVITY_UPDATE_THROTTLE
                    ):
                        local_db_session.query(UserModel).filter(
                            UserModel.id == user_id
                        ).update({"latest_activity": now})

                    # Convert to dict while object is still attached to session
                    user_dict = current_user.to_dict()
                
                request.state.current_user = user_dict

            except jwt.ExpiredSignatureError:
                raise GraphQLError("Signature has expired")
            except jwt.InvalidTokenError:
                raise GraphQLError("Authenticated Failed")

            return func(*args, **kwargs)

        return wrapper

    return decorator
