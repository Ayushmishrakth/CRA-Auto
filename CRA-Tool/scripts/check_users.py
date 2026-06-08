"""List users and columns in the DB."""
import asyncio, sys
sys.path.insert(0, ".")

from app.db.session import AsyncSessionLocal
from sqlalchemy import text


async def check():
    async with AsyncSessionLocal() as db:
        # get column names first
        cols = await db.execute(text("PRAGMA table_info(users)"))
        print("Columns:", [c[1] for c in cols.fetchall()])
        result = await db.execute(text("SELECT * FROM users LIMIT 10"))
        rows = result.fetchall()
        if not rows:
            print("No users found")
        for r in rows:
            print(r)


if __name__ == "__main__":
    asyncio.run(check())
