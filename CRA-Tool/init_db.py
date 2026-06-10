#!/usr/bin/env python
"""Initialize CRA database with essential data."""

import sqlite3
import sys
from pathlib import Path

def init_database():
    """Initialize database with essential data."""

    print("[INFO] Initializing CRA Database")
    print("=" * 70)

    db_path = Path("cra.db")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Check if tables exist
        print("[CHECK] Verifying tables...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        if not tables:
            print("[FAIL] No tables found. Run: python -m alembic upgrade head")
            return False

        print(f"[OK] Found {len(tables)} tables")

        # Check if we have users
        print("[CHECK] Checking users table...")
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count == 0:
            print("[WARN] No users found. Creating test user...")
            import uuid
            user_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO users (id, microsoft_oid, microsoft_tid, email, display_name, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'utc'), datetime('now', 'utc'))
            """, (
                user_id,
                "00000000-0000-0000-0000-000000000001",
                "fe4eff9a-f69c-48c0-921d-8006a6d5beb2",
                "admin@test.local",
                "Test Admin",
                "admin",
                1,
            ))
            conn.commit()
            print(f"[OK] Test user created: {user_id}")
        else:
            print(f"[OK] Found {user_count} user(s)")
            cursor.execute("SELECT email, display_name FROM users")
            for email, name in cursor.fetchall():
                print(f"     - {email} ({name})")

        # Check connected_tenants
        print("[CHECK] Checking connected_tenants table...")
        cursor.execute("SELECT COUNT(*) FROM connected_tenants")
        tenant_count = cursor.fetchone()[0]
        print(f"[OK] Found {tenant_count} tenant(s)")

        # Check assessments
        print("[CHECK] Checking assessments table...")
        cursor.execute("SELECT COUNT(*) FROM assessments")
        assessment_count = cursor.fetchone()[0]
        print(f"[OK] Found {assessment_count} assessment(s)")

        print("\n" + "=" * 70)
        print("[SUCCESS] Database is ready for assessments!")
        print("\nNext steps:")
        print("1. Start backend:  python -m uvicorn app.main:app --reload")
        print("2. Start frontend: npm run dev (in CRA-frontend directory)")
        print("3. Login at http://localhost:3000")

        return True

    except Exception as e:
        print(f"[FAIL] Database error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main entry point."""
    success = init_database()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
