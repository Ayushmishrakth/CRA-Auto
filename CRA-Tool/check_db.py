#!/usr/bin/env python
"""Check and initialize SQLite database for CRA."""

import sqlite3
import sys
import asyncio
from pathlib import Path

async def check_database():
    """Check if database exists and has tables."""
    db_path = Path("cra.db")

    if not db_path.exists():
        print("[FAIL] Database file not found: cra.db")
        return False

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get all tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            print("[FAIL] Database exists but has NO tables")
            conn.close()
            return False

        print(f"[OK] Database tables found ({len(tables)} total):\n")
        for table in tables:
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  [OK] {table:30s} - {count:6d} rows")

        conn.close()
        return True

    except Exception as e:
        print(f"[FAIL] Error checking database: {e}")
        return False

async def main():
    print("=" * 70)
    print("CRA DATABASE CHECK")
    print("=" * 70)
    print()

    success = await check_database()

    if success:
        print("\n[OK] Database is ready!")
        sys.exit(0)
    else:
        print("\n[FAIL] Database setup incomplete. Run migrations:")
        print("   python -m alembic upgrade head")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
