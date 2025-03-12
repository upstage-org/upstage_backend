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

from global_config import global_session, encrypt
from users.db_models.user import SUPER_ADMIN, UserModel


def create_some_users():
    for i in range(17, 18):
        user = UserModel(
            username=f"quang{i}",
            password=encrypt(f"Secret@123{i}"),
            email=f"quang{i}@no.none",
            active=True,
            role=SUPER_ADMIN,
        )
        global_session.add(user)
    global_session.commit()
    global_session.close()


def modify_user():
    db_session = global_session
    user = db_session.query(UserModel).filter(UserModel.username == "gloria2").one()
    user.password = encrypt("")
    # user.email = ("",)
    db_session.commit()


if __name__ == "__main__":
    create_some_users()
    # modify_user()
    # pass
