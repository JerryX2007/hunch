"""Create a nurse account (live Supabase data). Run from backend/:

    python -m scripts.create_nurse --email dana@example.com --name "Dana Lee" --role RN

Asks for the password (not shown as you type). Creates the Supabase Auth user with the
email already confirmed, plus their profile. Running it again for an existing email
updates the name, role and password. Needs SUPABASE_SERVICE_ROLE_KEY in backend/.env.
"""

import argparse
import getpass
import sys

from app import database as db

ROLES = ("RN", "RPN", "NP")

p = argparse.ArgumentParser(description="Create or update a nurse account.")
p.add_argument("--email", required=True)
p.add_argument("--name", required=True, help='Full name, e.g. "Dana Lee"')
p.add_argument("--role", required=True, choices=ROLES)
args = p.parse_args()

password = getpass.getpass("Password (8+ characters): ")
if len(password) < 8:
    sys.exit("Password must be at least 8 characters.")
if getpass.getpass("Same password again: ") != password:
    sys.exit("Passwords don't match.")

admin = db._require_admin().auth.admin
email = args.email.strip().lower()

existing = next((u for u in admin.list_users(per_page=1000) if (u.email or "").lower() == email), None)
if existing:
    admin.update_user_by_id(existing.id, {"password": password, "user_metadata": {"full_name": args.name}})
    user_id = existing.id
    print(f"Updated {email}.")
else:
    res = admin.create_user({"email": email, "password": password, "email_confirm": True,
                             "user_metadata": {"full_name": args.name}})
    user_id = res.user.id
    print(f"Created {email}.")

try:
    db.upsert_profile({"id": user_id, "full_name": args.name, "role": args.role})
except Exception as e:  # noqa: BLE001
    if "profiles_role_check" in str(e):
        sys.exit("The account exists, but the database rejected the role. Run "
                 "db/migrations/009_profile_roles.sql in the Supabase SQL Editor, then run this again.")
    raise
print(f"{args.name} ({args.role}) can now sign in to the nurse screen.")
