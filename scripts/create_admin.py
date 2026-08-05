"""
Creates (or promotes) an admin user interactively. Run via `make create-admin`.

The public /register form only ever creates regular users - letting
self-registration pick a role would be a privilege-escalation hole. This is
the only way to get an admin account.
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models.user import Role, User
from app.services.auth import hash_password

MIN_PASSWORD_LENGTH = 8


def prompt_email() -> str:
    email = input("Admin email: ").strip()
    if not email or "@" not in email:
        print("A valid email is required.", file=sys.stderr)
        sys.exit(1)
    return email


def prompt_password() -> str:
    password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
            file=sys.stderr,
        )
        sys.exit(1)
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        sys.exit(1)
    return password


def main() -> None:
    init_db()
    email = prompt_email()

    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()

        if user is not None:
            if user.role == Role.admin:
                print(f"{email} is already an admin. Nothing to do.")
                return
            user.role = Role.admin
            session.add(user)
            session.commit()
            print(f"Existing user {email} promoted to admin.")
            return

        password = prompt_password()
        user = User(email=email, password_hash=hash_password(password), role=Role.admin)
        session.add(user)
        session.commit()
        print(f"Admin user {email} created.")


if __name__ == "__main__":
    main()
