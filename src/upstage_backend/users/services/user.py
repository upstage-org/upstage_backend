# -*- coding: iso8859-15 -*-


from operator import or_
import asyncio

from fastapi import Request
from graphql import GraphQLError
import pyotp
import requests
from upstage_backend.global_config import get_session, logger
from upstage_backend.global_config.env import (
    ENV_TYPE,
    CLOUDFLARE_CAPTCHA_SECRETKEY,
    CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT,
    SUPPORT_EMAILS,
    HOSTNAME,
)

from upstage_backend.mails.helpers.mail import send
from upstage_backend.mails.templates.templates import (
    admin_registration_notification,
    password_reset,
    user_registration,
)
from upstage_backend.stages.services.stage_operation import StageOperationService
from upstage_backend.users.db_models.user import PLAYER, SUPER_ADMIN, UserModel
from upstage_backend.users.db_models.one_time_totp import OneTimeTOTPModel

# (connect, read) seconds for the Cloudflare Turnstile siteverify call.
CAPTCHA_VERIFY_TIMEOUT = (3.05, 5)


class UserService:
    def __init__(self):
        self.stage_operation_service = StageOperationService()

    def find_one(self, username: str, email: str):
        session = get_session()
        return (
            session.query(UserModel)
            .filter(or_(UserModel.username == username, UserModel.email == email))
            .first()
        )

    def find_by_id(self, user_id: int):
        session = get_session()
        return (
            session.query(UserModel)
            .filter(UserModel.id == user_id, UserModel.active.is_(True))
            .first()
        )

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
        user.role = PLAYER if not user.role else user.role
        user.active = True if user.role == SUPER_ADMIN else False
        user.email = data.get("email", "")
        user.first_name = data.get("firstName", "")
        user.last_name = data.get("lastName", "")
        user.username = data.get("username", "")
        user.intro = data.get("intro", "")
        session.add(user)
        session.flush()

        user = session.query(UserModel).filter(UserModel.username == data["username"]).first()

        asyncio.create_task(send([user.email], "Welcome to UpStage!", user_registration(user)))
        admin_emails = SUPPORT_EMAILS
        approval_url = f"https://{HOSTNAME}/admin/player?sortByCreated=true"
        asyncio.create_task(
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
            )
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

    def update(self, user: UserModel):
        session = get_session()
        session.query(UserModel).filter(UserModel.id == user.id).update({**user.to_dict()})
        session.flush()

    async def request_password_reset(self, email: str):
        session = get_session()
        user = (
            session.query(UserModel)
            .filter(or_(UserModel.email == email, UserModel.username == email))
            .first()
        )

        if not user:
            raise GraphQLError("User does not exist")
        totp = pyotp.TOTP(pyotp.random_base32())
        otp = totp.now()

        session.query(OneTimeTOTPModel).filter(OneTimeTOTPModel.user_id == user.id).delete()

        session.flush()
        session.add(OneTimeTOTPModel(user_id=user.id, code=otp))
        session.flush()

        asyncio.create_task(
            send(
                [user.email],
                f"Password reset for account {user.username}",
                password_reset(user, otp),
            )
        )

        return {
            "success": True,
            "message": f"We've sent an email with a code to reset your password to {email}.",
        }

    async def verify_password_reset(self, input):
        session = get_session()
        otp = (
            session.query(OneTimeTOTPModel).filter(OneTimeTOTPModel.code == input["token"]).first()
        )

        if not otp:
            raise GraphQLError("Invalid token")

        user = session.query(UserModel).filter(UserModel.id == otp.user_id).first()

        if not user:
            raise GraphQLError("Invalid token")

        return {
            "success": True,
            "message": "Token verified. Please reset your password.",
        }

    async def reset_password(self, input):
        session = get_session()
        otp = (
            session.query(OneTimeTOTPModel).filter(OneTimeTOTPModel.code == input["token"]).first()
        )

        if not otp:
            raise GraphQLError("Invalid token")

        user = session.query(UserModel).filter(UserModel.id == otp.user_id).first()

        if not user:
            raise GraphQLError("Invalid token")

        from upstage_backend.global_config.helpers.password import hash_password

        user.password = hash_password(input["password"])
        session.delete(otp)
        return {"success": True, "message": "Password reset successfully."}
