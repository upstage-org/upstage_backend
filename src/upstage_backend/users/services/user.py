# -*- coding: iso8859-15 -*-
import os
import sys


from operator import or_
import asyncio

from fastapi import Request
from graphql import GraphQLError
import pyotp
import requests
from upstage_backend.global_config import get_session
from upstage_backend.global_config.env import (ENV_TYPE,
    CLOUDFLARE_CAPTCHA_SECRETKEY,
    CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT,
    SUPPORT_EMAILS,
    HOSTNAME)

from upstage_backend.mails.helpers.mail import send
from upstage_backend.mails.templates.templates import (
    admin_registration_notification,
    password_reset,
    user_registration,
)
from upstage_backend.stages.services.stage_operation import StageOperationService
from upstage_backend.users.db_models.user import PLAYER, SUPER_ADMIN, UserModel
from upstage_backend.users.http.validation import CreateUserInput
from upstage_backend.users.db_models.one_time_totp import OneTimeTOTPModel


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

    async def create(self, data: CreateUserInput, request: Request):
        self.verify_captcha(data["token"], request)
        del data["token"]

        existing_user = self.find_one(data["username"], data.get("email", ""))
        if existing_user:
            raise GraphQLError("User already exists")

        from upstage_backend.global_config.helpers.fernet_crypto import encrypt

        session = get_session()
        user = UserModel()
        user.password = encrypt(data["password"])
        user.role = PLAYER if not user.role else user.role
        user.active = True if user.role == SUPER_ADMIN else False
        user.email = data.get("email", "")
        user.first_name = data.get("firstName", "")
        user.last_name = data.get("lastName", "")
        user.username = data.get("username", "")
        user.intro = data.get("intro", "")
        session.add(user)
        session.flush()

        user = (
            session.query(UserModel)
            .filter(UserModel.username == data["username"])
            .first()
        )

        asyncio.create_task(
            send([user.email], f"Welcome to UpStage!", user_registration(user))
        )
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

    def verify_captcha(self, token: str, request: Request):
        if ENV_TYPE != "Production":
            return

        if not CLOUDFLARE_CAPTCHA_SECRETKEY:
            return

        cf_ip = request.headers.get("CF-Connecting-IP")
        ip = request.headers.get("X-Forwarded-For", request.client.host)
        if type(ip) == list:
            ip = ip[0]

        """
        Allow CloudFlare to be turned off for testing.
        """
        formData = {
            "secret": CLOUDFLARE_CAPTCHA_SECRETKEY,
            "response": token,
            "remoteip": cf_ip or ip,
        }

        result = requests.post(CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT, data=formData)
        outcome = result.json()
        print(f"************* Using {ip} or {cf_ip} , outcome: {outcome} ****")

        if not outcome["success"]:
            raise GraphQLError(
                "We think you are not a human! " + ", ".join(outcome["error-codes"])
            )

    def update(self, user: UserModel):
        session = get_session()
        session.query(UserModel).filter(UserModel.id == user.id).update(
            {**user.to_dict()}
        )
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

        session.query(OneTimeTOTPModel).filter(
            OneTimeTOTPModel.user_id == user.id
        ).delete()

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
            session.query(OneTimeTOTPModel)
            .filter(OneTimeTOTPModel.code == input["token"])
            .first()
        )

        if not otp:
            raise GraphQLError("Invalid token")

        user = (
            session.query(UserModel)
            .filter(UserModel.id == otp.user_id)
            .first()
        )

        if not user:
            raise GraphQLError("Invalid token")

        return {
            "success": True,
            "message": "Token verified. Please reset your password.",
        }

    async def reset_password(self, input):
        session = get_session()
        otp = (
            session.query(OneTimeTOTPModel)
            .filter(OneTimeTOTPModel.code == input["token"])
            .first()
        )

        if not otp:
            raise GraphQLError("Invalid token")

        user = (
            session.query(UserModel)
            .filter(UserModel.id == otp.user_id)
            .first()
        )

        if not user:
            raise GraphQLError("Invalid token")

        from upstage_backend.global_config.helpers.fernet_crypto import encrypt

        user.password = encrypt(input["password"])
        session.delete(otp)
        return {"success": True, "message": "Password reset successfully."}
