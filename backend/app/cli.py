"""Admin commands.

python -m app.cli reset-password <email>        prompt for a new password
python -m app.cli reset-password <email> --generate   print a random one
python -m app.cli make-admin <email>
python -m app.cli remove-admin <email>
python -m app.cli check-db                      test the database connection
"""

import argparse
import asyncio
import getpass
import secrets
import sys

from sqlalchemy import make_url, text

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.schemas.auth import PASSWORD_MAX, PASSWORD_MIN
from app.services import auth_service


async def _reset_password(email: str, password: str) -> bool:
    async with SessionLocal() as session:
        return await auth_service.set_password(session, email, password)


async def _set_admin(email: str, value: bool) -> bool:
    async with SessionLocal() as session:
        return await auth_service.set_admin(session, email, value)


async def _check_db() -> None:
    url = make_url(get_settings().database_url)
    print(f"Connecting to {url.host} / {url.database} as {url.username} ...")
    async with engine.connect() as conn:
        version = (await conn.execute(text("SHOW server_version"))).scalar()
        has_tables = (
            await conn.execute(text("SELECT to_regclass('public.alembic_version') IS NOT NULL"))
        ).scalar()
        revision = None
        if has_tables:
            revision = (
                await conn.execute(text("SELECT version_num FROM alembic_version"))
            ).scalar()
    print(f"Connected. PostgreSQL {version}.")
    print(
        f"B.A.B tables at migration {revision}."
        if revision
        else "No B.A.B tables yet (the API creates them on its first start)."
    )


def _ask_password() -> str:
    while True:
        first = getpass.getpass("New password: ")
        if not PASSWORD_MIN <= len(first) <= PASSWORD_MAX:
            print(f"Use {PASSWORD_MIN} to {PASSWORD_MAX} characters.")
            continue
        if getpass.getpass("Repeat it: ") != first:
            print("The two entries differ. Try again.")
            continue
        return first


async def _run(coro):
    try:
        return await coro
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="B.A.B admin commands")
    sub = parser.add_subparsers(dest="command", required=True)
    rp = sub.add_parser("reset-password", help="Set a new password and sign the user out")
    rp.add_argument("email")
    rp.add_argument("--generate", action="store_true", help="Generate and print a password")
    for name in ("make-admin", "remove-admin"):
        sub.add_parser(name).add_argument("email")
    sub.add_parser("check-db", help="Test the database connection (uses BAB_DATABASE_URL)")
    args = parser.parse_args(argv)

    if args.command == "check-db":
        try:
            asyncio.run(_run(_check_db()))
        except Exception as exc:  # show the reason, never the connection string
            print(f"Could not connect: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.command == "reset-password":
        password = secrets.token_urlsafe(12) if args.generate else _ask_password()
        if not asyncio.run(_run(_reset_password(args.email, password))):
            print(f"No user with email {args.email}.", file=sys.stderr)
            return 1
        print("Password updated. All sessions for this user were signed out.")
        if args.generate:
            print(f"New password: {password}")
        return 0

    is_admin = args.command == "make-admin"
    if not asyncio.run(_run(_set_admin(args.email, is_admin))):
        print(f"No user with email {args.email}.", file=sys.stderr)
        return 1
    print(f"{args.email} is {'now' if is_admin else 'no longer'} an admin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
