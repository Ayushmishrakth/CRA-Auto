#!/usr/bin/env python
"""Test required Python imports."""

import sys

print('Python version:', sys.version.split()[0])
print('Checking key imports...')

modules = ['fastapi', 'sqlalchemy', 'aiosqlite', 'jwt', 'redis', 'httpx']
failed = []

for module in modules:
    try:
        __import__(module)
        print(f'[OK] {module}')
    except ImportError:
        print(f'[FAIL] {module}')
        failed.append(module)

if failed:
    print(f'\nMissing modules: {", ".join(failed)}')
    print('Run: pip install -r requirements.txt')
    sys.exit(1)
else:
    print('\n[SUCCESS] All dependencies installed!')
    sys.exit(0)
