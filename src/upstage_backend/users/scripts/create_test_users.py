# -*- coding: iso8859-15 -*-
import os
import sys

from upstage_backend.global_config.database import ScopedSession
from upstage_backend.global_config.helpers.fernet_crypto import encrypt
from upstage_backend.users.db_models.user import SUPER_ADMIN, UserModel


def create_some_users():
    with ScopedSession() as s:
        for i in range(17, 18):
            user = UserModel(
                username=f"quang{i}",
                password=encrypt(f"Secret@123{i}"),
                email=f"quang{i}@no.none",
                active=True,
                role=SUPER_ADMIN,
            )
            s.add(user)


def modify_user():
    with ScopedSession() as s:
        user = s.query(UserModel).filter(UserModel.username == "gloria2").one()
        user.password = encrypt("")


if __name__ == "__main__":
    create_some_users()
    # modify_user()
    # pass
