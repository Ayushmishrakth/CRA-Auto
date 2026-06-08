"""Generate a CRA JWT for API calls."""
import sys
sys.path.insert(0, ".")

from app.core.security import create_access_token

token = create_access_token(
    sub="92207583-c2f4-450e-b564-07d97a64f94e",  # deep@wealthscape.in
    tid="fe4eff9a-f69c-48c0-921d-8006a6d5beb2",
    email="deep@wealthscape.in",
    role="admin",
    connected_tenants=["fe4eff9a-f69c-48c0-921d-8006a6d5beb2"],
)
print(token)
