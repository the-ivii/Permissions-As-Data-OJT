"""In-memory cache for active authorization policy."""
ACTIVE_POLICY_CACHE = {"policy": None}

# Purpose:
# Cache avoids repeated database queries for active policy
# 
# How It Works:
# - Cache hit: If the policy is cached, use it (no database query).
# - Cache miss: If not cached, fetch from the database and store it in the cache.
# - Cache invalidation: When a new policy is activated, the cache is updated.
#
# Where it is used:
# - In authorization service for authorization checks.
# - In crud.py for updating the active policy in cache.
# 
# Note: Can be replaced with Redis later for scalability.

