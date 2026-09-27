from sqlalchemy import TIMESTAMP, BigInteger, Boolean, Integer, String, Text, text
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from upstage_backend.global_config.helpers.clock import utcnow
from upstage_backend.global_config.db_models.base import BaseModel


PLAYER = 1
GUEST = 4
ADMIN = 8
SUPER_ADMIN = 32
ROLES = {
    PLAYER: "Player",  # Player access to on-stage tools
    GUEST: "Guest",  # Can play a stage if granted player permission, cannot create or edit media
    ADMIN: "Admin",  # Admin access to edit media, players, content
    SUPER_ADMIN: "Super Admin",  # Internal Upstage staff access to all
}


class UserModel(BaseModel):
    __tablename__ = "upstage_user"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True, default="")
    password: Mapped[str] = mapped_column(Text, nullable=False, default="")
    email: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    bin_name: Mapped[str | None] = mapped_column(Text, nullable=True, default="")
    role: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_name: Mapped[str | None] = mapped_column(String, default="")
    last_name: Mapped[str | None] = mapped_column(String, default="")
    display_name: Mapped[str | None] = mapped_column(String, default="")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    firebase_pushnot_id: Mapped[str | None] = mapped_column(String, default=None)
    created_on: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=utcnow)
    deactivated_on: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None)
    # server_default mirrors alembic c3d5e7f9a1b2: NULL is never "unlimited"
    # (users.services.upload_limit reads it as this default anyway).
    upload_limit: Mapped[int | None] = mapped_column(
        Integer, default=1024 * 1024, server_default=text("1048576")
    )
    intro: Mapped[str | None] = mapped_column(Text, default=None)
    can_send_email: Mapped[bool | None] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None)

    # Fields that any authenticated user may see about another user (player
    # pickers in Media permissions / Stage filters). Everything else (email,
    # intro, upload limit, ...) is admin-only.
    PUBLIC_FIELDS = (
        "id",
        "username",
        "display_name",
        "first_name",
        "last_name",
        "role",
        "active",
        "created_on",
    )

    def to_dict(self, visited=None):
        """
        Never serialise the password hash. `BaseModel.to_dict` walks every
        column, and User dicts end up in GraphQL responses through
        `Stage.owner`, `Asset.owner`, `adminPlayers`, `users` and `whoami`.
        """
        data = super().to_dict(visited)
        if data is not None:
            data.pop("password", None)
        return data

    def to_public_dict(self):
        data = self.to_dict() or {}
        return {key: data.get(key) for key in self.PUBLIC_FIELDS}
