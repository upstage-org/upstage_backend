from datetime import timedelta
from graphql import GraphQLError
import uuid

import jwt
from fastapi import Request
from sqlalchemy import delete, select, update
from email.utils import parseaddr
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.authentication.http.validation import LoginInput
from upstage_backend.users.db_models.user import (
    ADMIN,
    GUEST,
    PLAYER,
    SUPER_ADMIN,
    UserModel,
)
from upstage_backend.users.services.user import UserService
from upstage_backend.global_config.helpers.password import verify_password
from upstage_backend.global_config.env import (
    ENV_TYPE,
    JWT_ADMIN_TOKEN_DAYS,
    JWT_HEADER_NAME,
    JWT_USER_TOKEN_DAYS,
    SECRET_KEY,
    ALGORITHM,
)
from upstage_backend.global_config import get_session as get_request_session
from upstage_backend.authentication.db_models.user_session import UserSessionModel


class AuthenticationService:
    def __init__(self):
        self.user_service = UserService()

    async def login(self, dto: LoginInput, request: Request):
        await self.user_service.verify_captcha_async(dto.token, request)

        username, password = dto.username, dto.password

        email = self.validate_login_payload(username)
        user = self.user_service.find_one(username, email)
        if not user:
            raise GraphQLError("Incorrect username or password. Please try again.")

        self.validate_password(password, user)
        access_token, refresh_token = self.create_token_pair(user)

        user_session = UserSessionModel(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            app_version=request.headers.get("X-Upstage-App-Version"),
            app_os_type=request.headers.get("X-Upstage-Os-Type"),
            app_os_version=request.headers.get("X-Upstage-Os-Version"),
            app_device=request.headers.get("X-Upstage-Device-Model"),
        )

        user.last_login = utcnow()

        db = get_request_session()
        db.add(user_session)
        db.flush()

        db.execute(update(UserModel).where(UserModel.id == user.id).values(last_login=utcnow()))

        title_prefix = "" if ENV_TYPE == "Production" else "DEV "
        default_title = title_prefix + "Upstage"
        title = default_title
        groups = []
        group = None

        if user.role == SUPER_ADMIN:
            title = title_prefix + "Super Admin"
            group = {"id": 0, "name": "test"}
            groups = [group]

        elif user.role in (PLAYER, GUEST, ADMIN) and not (group):
            group = {"id": 0, "name": "test"}
            groups = [group]

        return dict(
            {
                "user_id": user.id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "role": user.role,
                "first_name": user.first_name,
                "groups": groups,
                "username": user.username,
                "title": title,
            }
        )

    def validate_login_payload(self, username: str):
        username = username.strip()
        if "@" in username:
            return parseaddr(username)[1]

        return username

    def validate_password(self, enter_password: str, user: UserModel):
        if not verify_password(user.password, enter_password):
            raise GraphQLError("Incorrect username or password. Please try again.")
        if not user.active:
            raise GraphQLError(
                "Your account has been successfully created but not approved yet.<br/>Please wait for approval or contact UpStage Admin for support!"
            )

    @staticmethod
    def token_lifetime(role) -> timedelta:
        """
        How long a login lasts: JWT_ADMIN_TOKEN_DAYS for admins and super
        admins, JWT_USER_TOKEN_DAYS for everyone else.
        """
        days = JWT_ADMIN_TOKEN_DAYS if role in (ADMIN, SUPER_ADMIN) else JWT_USER_TOKEN_DAYS
        return timedelta(days=days)

    def create_token_pair(self, user: UserModel) -> tuple[str, str]:
        """
        A fresh (access token, refresh token) pair for `user`, both valid for
        the user's role lifetime. The refresh token does not outlive the
        access token: the client renews the pair while it is still valid (it
        schedules that ahead of the expiry); once the lifetime has passed
        without a renewal, the user logs in again.
        """
        lifetime = self.token_lifetime(user.role)
        access_token = self.create_token({"user_id": user.id}, lifetime)
        refresh_token = self.create_token({"user_id": user.id, "type": "refresh"}, lifetime)
        return access_token, refresh_token

    def create_token(self, data: dict, exp: timedelta):
        to_encode = data.copy()
        # `jti` makes every token distinct. Without it two tokens issued to
        # one user within the same second were identical, so a refresh right
        # after a login "rotated" the refresh token into itself and the used
        # token stayed valid.
        to_encode.update({"exp": utcnow() + exp, "jti": uuid.uuid4().hex})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    async def logout(self, request: Request):
        bearer_token = request.headers.get("Authorization", "").split(" ")
        if len(bearer_token) != 2:
            raise GraphQLError("Invalid access token")

        access_token = bearer_token[1]
        db = get_request_session()
        user_session = db.scalars(
            select(UserSessionModel).where(UserSessionModel.access_token == access_token).limit(1)
        ).first()
        if not user_session:
            raise GraphQLError("Invalid access token")
        db.delete(user_session)

        return "Logged out"

    async def refresh_token(self, request: Request):
        current_refresh_token = request.headers.get(JWT_HEADER_NAME)
        if not current_refresh_token:
            raise GraphQLError("Invalid refresh token")

        # The token used to be looked up in the DB only, so its `exp` and
        # `type` claims were never enforced: a leaked refresh token worked
        # for as long as the session row survived.
        try:
            claims = jwt.decode(current_refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise GraphQLError("Invalid refresh token") from None
        except jwt.InvalidTokenError:
            raise GraphQLError("Invalid refresh token") from None
        if claims.get("type") != "refresh":
            raise GraphQLError("Invalid refresh token")

        db = get_request_session()
        session = db.scalars(
            select(UserSessionModel)
            .where(UserSessionModel.refresh_token == current_refresh_token)
            .limit(1)
        ).first()

        if not session or session.user_id != claims.get("user_id"):
            raise GraphQLError("Invalid refresh token")

        user = db.scalars(select(UserModel).where(UserModel.id == session.user_id).limit(1)).first()
        if not user or not user.active:
            db.delete(session)
            raise GraphQLError("Invalid refresh token")

        access_token, refresh_token = self.create_token_pair(user)

        db.execute(
            delete(UserSessionModel).where(UserSessionModel.refresh_token == current_refresh_token)
        )

        user_session = UserSessionModel(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            app_version=request.headers.get("X-Upstage-App-Version"),
            app_os_type=request.headers.get("X-Upstage-Os-Type"),
            app_os_version=request.headers.get("X-Upstage-Os-Version"),
            app_device=request.headers.get("X-Upstage-Device-Model"),
        )
        db.add(user_session)
        db.flush()

        db.execute(update(UserModel).where(UserModel.id == user.id).values(last_login=utcnow()))

        return {"access_token": access_token, "refresh_token": refresh_token}

    def get_session(self, token: str, user_id: int):
        db = get_request_session()
        return db.scalars(
            select(UserSessionModel)
            .where(
                UserSessionModel.user_id == user_id,
                UserSessionModel.access_token == token,
            )
            .limit(1)
        ).first()
