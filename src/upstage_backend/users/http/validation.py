# -*- coding: iso8859-15 -*-
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ValidationError

# Limits mirror UpdateUserInput (studio_management/http/validation.py) so a
# user accepted at registration always survives the admin update path — the
# admin status toggle re-submits the whole record through that model. All
# max_length limits count characters, not bytes, so multibyte scripts
# (e.g. Cyrillic) are not penalized.


class CreateUserInput(BaseModel):
    # min 2 matches the registration form's own check; max 100 matches
    # BatchUserInput/UpdateUserInput (existing usernames run past the old 10).
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, max_length=256)
    email: EmailStr
    # The registration form treats first/last name as optional.
    firstName: Optional[str] = Field(None, max_length=100)
    lastName: Optional[str] = Field(None, max_length=100)
    intro: str = Field(..., min_length=1, max_length=5000)
    # Null outside Production (the form sends token: null); in Production a
    # missing token still fails Cloudflare verification in verify_captcha.
    token: Optional[str] = None


# Shown to the registering user as the GraphQL error message.
_FIELD_LABELS = {
    "username": "Username",
    "password": "Password",
    "email": "Email",
    "firstName": "First name",
    "lastName": "Last name",
    "intro": "Introduction",
}


def format_validation_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = err.get("loc") or ()
        field = str(loc[0]) if loc else "input"
        label = _FIELD_LABELS.get(field, field)
        msg = err.get("msg", "is invalid")
        if err.get("type") == "missing":
            msg = "is required"
        parts.append(f"{label}: {msg}")
    return "; ".join(parts)
