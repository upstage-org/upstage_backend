# -*- coding: iso8859-15 -*-

from upstage_backend.global_config.database import ScopedSession
from upstage_backend.global_config.helpers.password import hash_password
from upstage_backend.users.db_models.user import SUPER_ADMIN, UserModel


def create_some_users():
    with ScopedSession() as s:
        for i in range(17, 18):
            user = UserModel(
                username=f"quang{i}",
                password=hash_password(f"Secret@123{i}"),
                email=f"quang{i}@no.none",
                active=True,
                role=SUPER_ADMIN,
            )
            s.add(user)


def modify_user():
    with ScopedSession() as s:
        user = s.query(UserModel).filter(UserModel.username == "gloria2").one()
        user.password = hash_password("")


if __name__ == "__main__":
    create_some_users()
    # modify_user()
    # pass
