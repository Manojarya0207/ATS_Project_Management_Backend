"""Bootstrap script: create the initial admin account.

Usage:
    python scripts/seed_admin.py [email] [password] [full_name]

Defaults: admin@ats.com / Admin@12345 / "System Administrator"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth.password import hash_password  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402
from app.models import User, UserRole  # noqa: E402


def main() -> None:
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@ats.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "Admin@12345"
    full_name = sys.argv[3] if len(sys.argv) > 3 else "System Administrator"

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"Admin already exists: {email}")
            return
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=UserRole.admin,
        )
        db.add(user)
        db.commit()
        print(f"Admin created: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
