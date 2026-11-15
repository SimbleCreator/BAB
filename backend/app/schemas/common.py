import re

from pydantic import BaseModel

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not _EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address.")
    return value


class ErrorOut(BaseModel):
    detail: str
    code: str


class MessageOut(BaseModel):
    message: str
