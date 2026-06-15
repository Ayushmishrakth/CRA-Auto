#!/usr/bin/env python3
"""
Check logs for logo-related messages.
"""

from pathlib import Path
from datetime import datetime, timedelta
import re

print("=" * 80)
print("LOG DIAGNOSTIC")
print("=" * 80)

# Look for log files
log_files = []

# Common log locations
search_paths = [
    Path("."),
    Path("logs"),
    Path("app"),
]

print(f"\n1. SEARCHING FOR LOG FILES")

for search_path in search_paths:
    if search_path.exists():
        for log_file in search_path.rglob("*.log"):
            log_files.append(log_file)
            print(f"   Found: {log_file}")

if not log_files:
    print(f"   ⚠️  No .log files found")
    print(f"   Logs may be going to console only")
    print(f"\n   Recommended: Run the app with logging redirected to file:")
    print(f"   python main.py 2>&1 | tee app.log")
    exit(0)

print(f"\n2. CHECKING LOG CONTENT FOR LOGO MESSAGES")

for log_file in log_files:
    print(f"\n   === {log_file.name} ===")

    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Look for key messages
        patterns = {
            "Logo Storage": r"\[CACHE\].*logo",
            "Logo Retrieval": r"\[CACHE\].*Retrieving.*logo",
            "Logo Processing": r"\[LOGO\]",
            "Report Generation": r"\[REPORT\]",
            "Word Report": r"render_word_report",
        }

        for pattern_name, pattern in patterns.items():
            matches = re.findall(f".*{pattern}.*", content, re.IGNORECASE)
            if matches:
                print(f"\n   ✅ {pattern_name}: {len(matches)} messages")
                for match in matches[-5:]:  # Show last 5
                    print(f"      {match[:120]}")
            else:
                print(f"   ❌ {pattern_name}: NOT FOUND")

        # Look for errors
        print(f"\n   Looking for errors...")
        errors = re.findall(r".*(?:ERROR|EXCEPTION|Failed|failed).*", content)
        if errors:
            print(f"   ⚠️  Errors found: {len(errors)}")
            for error in errors[-5:]:  # Show last 5
                print(f"      {error[:120]}")
        else:
            print(f"   ✅ No errors in logs")

    except Exception as e:
        print(f"   ❌ Error reading log: {e}")

print(f"\n" + "=" * 80)
print("NEXT STEPS")
print("=" * 80)
print(f"""
1. Run the template diagnostic:
   python check_template.py

2. Check storage directories exist:
   ls -la storage/

3. Restart app with logging to file:
   python main.py 2>&1 | tee app.log

4. Generate a report with logo

5. Check logs:
   python check_logs.py

6. Look for [LOGO], [CACHE], and [REPORT] messages
""")
