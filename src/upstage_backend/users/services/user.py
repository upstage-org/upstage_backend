import asyncio
import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import Request
from graphql import GraphQLError
import requests
from sqlalchemy import delete, or_, select
from upstage_backend.global_config.helpers.clock import as_utc, utcnow
from upstage_backend.authentication.db_models.user_session import UserSessionModel
from upstage_backend.global_config import get_session, logger
from upstage_backend.global_config.db_context import finish_request_transaction
from upstage_backend.global_config.env import (
    ENV_TYPE,
    CLOUDFLARE_CAPTCHA_SECRETKEY,
    CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT,
    SUPPORT_EMAILS,
    HOSTNAME,
)
from upstage_backend.global_config.helpers.background import spawn

from upstage_backend.mails.helpers.mail import send
from upstage_backend.mails.templates.templates import (
    admin_registration_notification,
    password_reset,
    user_registration,
)
from upstage_backend.stages.services.stage_operation import StageOperationService
from upstage_backend.users.db_models.user import PLAYER, UserModel
from upstage_backend.users.db_models.one_time_totp import OneTimeTOTPModel

# (connect, read) seconds for the Cloudflare Turnstile siteverify call.
CAPTCHA_VERIFY_TIMEOUT = (3.05, 5)

# Password-reset codes: 6 digits (the login form's input is maxlength=6 and
# the email copy says "6-digit"), valid for 30 minutes (matches the email),
# at most 5 wrong guesses before the code is discarded. Only the sha256 of the
# code is stored, and the lookup is scoped to the account named in the
# request, so a guess against one account cannot hit another's code.
PASSWORD_RESET_CODE_DIGITS = 6
PASSWORD_RESET_TTL = timedelta(minutes=30)
PASSWORD_RESET_MAX_ATTEMPTS = 5
PASSWORD_RESET_INVALID = "Invalid or expired code. Please request a new one."
# Same answer whether or not the account exists (no user enumeration).
PASSWORD_RESET_REQUESTED = (
    "If an account matches, we've sent an email with a code to reset your password."
)


def _hash_reset_code(code: str) -> str:
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def _lookup_user(session, email_or_username: str):
    value = (email_or_username or "").strip()
    if not value:
        return None
    return session.scalars(
        select(UserModel).where(or_(UserModel.email == value, UserModel.username == value)).limit(1)
    ).first()


def revoke_user_sessions(session, user_id: int, keep_access_token: str | None = None) -> None:
    """Delete every login session of `user_id` (after a password change/reset)."""
    statement = delete(UserSessionModel).where(UserSessionModel.user_id == user_id)
    if keep_access_token:
        statement = statement.where(UserSessionModel.access_token != keep_access_token)
    session.execute(statement, execution_options={"synchronize_session": False})


class UserService:
    def __init__(self):
        self.stage_operation_service = StageOperationService()

    def find_one(self, username: str, email: str):
        session = get_session()
        return session.scalars(
            select(UserModel)
            .where(or_(UserModel.username == username, UserModel.email == email))
            .limit(1)
        ).first()

    def find_by_id(self, user_id: int):
        session = get_session()
        return session.scalars(
            select(UserModel).where(UserModel.id == user_id, UserModel.active.is_(True)).limit(1)
        ).first()

    # `data` is the already-validated CreateUserInput as a plain dict
    # (the resolver runs the pydantic validation and passes model_dump()).
    async def create(self, data: dict, request: Request):
        await self.verify_captcha_async(data["token"], request)
        del data["token"]

        existing_user = self.find_one(data["username"], data.get("email", ""))
        if existing_user:
            raise GraphQLError("User already exists")

        from upstage_backend.global_config.helpers.password import hash_password

        session = get_session()
        user = UserModel()
        user.password = hash_password(data["password"])
        # Self-registration always creates an inactive PLAYER; an admin
        # approves it (the old `if not user.role` branch could never be
        # anything else on a fresh model).
        user.role = PLAYER
        user.active = False
        user.email = data.get("email", "")
        user.first_name = data.get("firstName", "")
        user.last_name = data.get("lastName", "")
        user.username = data.get("username", "")
        user.intro = data.get("intro", "")
        session.add(user)
        session.flush()

        user = session.scalars(
            select(UserModel).where(UserModel.username == data["username"]).limit(1)
        ).first()

        spawn(send([user.email], "Welcome to UpStage!", user_registration(user)))
        admin_emails = SUPPORT_EMAILS
        approval_url = f"https://{HOSTNAME}/admin/player?sortByCreated=true"
        spawn(
            send(
                admin_emails,
                f"Approval required for {user.username}'s registration",
                admin_registration_notification(user, approval_url),
            )
        )

        self.stage_operation_service.assign_user_to_default_stage([user.id])

        return {"user": user.to_dict()}

    async def verify_captcha_async(self, token: str, request: Request):
        """verify_captcha without stalling the server.

        Resolvers run on the uvicorn event loop, so the blocking HTTPS round
        trip to Cloudflare used to freeze EVERY request for its duration, on
        every production login and registration. It runs in a worker thread
        instead. Callers await this before touching the database, so no
        transaction is open while it is in flight.
        """
        await asyncio.to_thread(self.verify_captcha, token, request)

    def verify_captcha(self, token: str, request: Request):
        if ENV_TYPE != "Production":
            return

        if not CLOUDFLARE_CAPTCHA_SECRETKEY:
            return

        cf_ip = request.headers.get("CF-Connecting-IP")
        ip = request.headers.get("X-Forwarded-For", request.client.host)
        if isinstance(ip, list):
            ip = ip[0]

        """
        Allow CloudFlare to be turned off for testing.
        """
        formData = {
            "secret": CLOUDFLARE_CAPTCHA_SECRETKEY,
            "response": token,
            "remoteip": cf_ip or ip,
        }

        # requests has NO default timeout: without one, a stalled Cloudflare
        # connection would hang the caller forever. Fail closed on any
        # network/parse problem so an outage cannot be used to skip the check.
        try:
            result = requests.post(
                CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT,
                data=formData,
                timeout=CAPTCHA_VERIFY_TIMEOUT,
            )
            outcome = result.json()
        except (requests.RequestException, ValueError) as error:
            logger.warning("Cloudflare Turnstile verification unavailable: {}", error)
            raise GraphQLError(
                "We could not verify the captcha right now. Please try again in a moment."
            ) from None
        remoteip = cf_ip or ip

        if outcome.get("success"):
            logger.debug(
                "Cloudflare Turnstile verified (remoteip={}, cf_connecting_ip={})",
                remoteip,
                cf_ip,
            )
        else:
            error_codes = outcome.get("error-codes", [])
            logger.warning(
                "Cloudflare Turnstile verification failed (remoteip={}, cf_connecting_ip={}, error_codes={})",
                remoteip,
                cf_ip,
                error_codes,
            )
            raise GraphQLError("We think you are not a human! " + ", ".join(error_codes))

    async def request_password_reset(self, email: str):
        session = get_session()
        user = _lookup_user(session, email)

        if user and user.email:
            code = f"{secrets.randbelow(10**PASSWORD_RESET_CODE_DIGITS):0{PASSWORD_RESET_CODE_DIGITS}d}"

            session.execute(delete(OneTimeTOTPModel).where(OneTimeTOTPModel.user_id == user.id))
            session.flush()
            session.add(
                OneTimeTOTPModel(
                    user_id=user.id,
                    code=_hash_reset_code(code),
                    url="0",
                    recorded_time=utcnow(),
                )
            )
            session.flush()

            spawn(
                send(
                    [user.email],
                    f"Password reset for account {user.username}",
                    password_reset(user, code),
                )
            )

        return {"success": True, "message": PASSWORD_RESET_REQUESTED}

    def _consume_reset_attempt(self, session, email: str, token: str):
        """
        Return the (user, otp_row) pair when `token` is the live code for the
        account `email`; otherwise record the failed attempt and raise.

        A raised GraphQLError rolls the mutation back (see
        global_config.schema.end_transaction_after_root_mutation), so the
        attempt counter / discarded row is committed explicitly first.
        """
        user = _lookup_user(session, email)
        otp = (
            session.scalars(
                select(OneTimeTOTPModel).where(OneTimeTOTPModel.user_id == user.id).limit(1)
            ).first()
            if user
            else None
        )
        if not user or not otp:
            raise GraphQLError(PASSWORD_RESET_INVALID)

        if not otp.recorded_time or as_utc(otp.recorded_time) < utcnow() - PASSWORD_RESET_TTL:
            session.delete(otp)
            session.flush()
            finish_request_transaction(commit=True)
            raise GraphQLError(PASSWORD_RESET_INVALID)

        if not hmac.compare_digest(otp.code or "", _hash_reset_code(token)):
            try:
                attempts = int(otp.url or "0") + 1
            except ValueError:
                attempts = PASSWORD_RESET_MAX_ATTEMPTS
            if attempts >= PASSWORD_RESET_MAX_ATTEMPTS:
                session.delete(otp)
            else:
                otp.url = str(attempts)
            session.flush()
            finish_request_transaction(commit=True)
            raise GraphQLError(PASSWORD_RESET_INVALID)

        return user, otp

    async def verify_password_reset(self, input):
        session = get_session()
        self._consume_reset_attempt(session, input.email, input.token)
        return {
            "success": True,
            "message": "Token verified. Please reset your password.",
        }

    async def reset_password(self, input):
        session = get_session()
        user, otp = self._consume_reset_attempt(session, input.email, input.token)

        from upstage_backend.global_config.helpers.password import hash_password

        user.password = hash_password(input.password)
        session.delete(otp)
        # Every existing login of this account is invalidated: the reset
        # exists precisely because the credential may be in the wrong hands.
        revoke_user_sessions(session, user.id)
        session.flush()
        return {"success": True, "message": "Password reset successfully."}
