"""Create a nurse account (live Supabase data). Run from backend/:

    python -m scripts.create_nurse --email dana@example.com --name "Dana Lee"

Asks for the password (not shown as you type). Creates the Supabase Auth user with the
email already confirmed, plus their profile. Running it again for an existing email
updates the name and password. Needs SUPABASE_SERVICE_ROLE_KEY in backend/.env.
"""

import argparse
import getpass
import sys

from app import database as db


def ask_password(prompt: str = "Password (8+ characters): ") -> str:
    password = getpass.getpass(prompt)
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters.")
    if getpass.getpass("Same password again: ") != password:
        sys.exit("Passwords don't match.")
    return password


def upsert_nurse(email: str, name: str, password: str) -> str:
    """Create or update the account + profile. Returns the user ID."""
    admin = db._require_admin().auth.admin
    email = email.strip().lower()
    existing = next((u for u in admin.list_users(per_page=1000) if (u.email or "").lower() == email), None)
    if existing:
        admin.update_user_by_id(existing.id, {"password": password, "user_metadata": {"full_name": name}})
        user_id, verb = existing.id, "Updated"
    else:
        res = admin.create_user({"email": email, "password": password, "email_confirm": True,
                                 "user_metadata": {"full_name": name}})
        user_id, verb = res.user.id, "Created"
    try:
        db.upsert_profile({"id": user_id, "full_name": name, "role": "nurse"})
    except Exception as e:  # noqa: BLE001
        if "profiles_role_check" in str(e):
            sys.exit("The account exists, but the database rejected the role. Run "
                     "db/migrations/009_profile_roles.sql in the Supabase SQL Editor, then run this again.")
        raise
    print(f"  {verb} {name} <{email}>")
    return user_id


def main() -> None:
    p = argparse.ArgumentParser(description="Create or update a nurse account.")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True, help='Full name, e.g. "Dana Lee"')
    args = p.parse_args()
    upsert_nurse(args.email, args.name, ask_password())
    print(f"{args.name} can now sign in to the nurse screen.")


if __name__ == "__main__":
    main()
