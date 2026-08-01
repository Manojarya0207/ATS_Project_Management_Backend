"""Bootstrap script: create the initial admin account.

Usage:
    python scripts/seed_admin.py [email] [password] [full_name]

Defaults: admin@ats.com / Admin@12345 / "System Administrator"
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import Settings
from app.core.database import build_engine
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.shared.enums import UserRole


async def main() -> None:
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@ats.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "Admin@12345"
    full_name = sys.argv[3] if len(sys.argv) > 3 else "System Administrator"

    settings = Settings()
    engine, sessionmaker = build_engine(settings)
    try:
        async with sessionmaker() as db:
            users = UserRepository(db)
            if await users.get_by_email(email) is not None:
                print(f"Admin already exists: {email}")
                return
            await users.add(
                User(
                    email=email,
                    hashed_password=await hash_password(password),
                    full_name=full_name,
                    role=UserRole.admin,
                )
            )
            await db.commit()
            print(f"Admin created: {email}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
