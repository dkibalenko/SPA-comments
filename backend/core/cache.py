from django.core.cache import cache

# TTLs
COMMENT_LIST_TTL = 60       # 60 seconds - short, list changes often
COMMENT_TREE_TTL = 300      # 5 minutes - trees change less frequently


def make_list_cache_key(ordering: str, page: int) -> str:
    """Deterministic cache key for a paginated comment list page.

    Example: "comments:list:ordering=-created_at:page=1"
    """
    return f"comments:list:ordering={ordering}:page={page}"


def make_tree_cache_key(root_id: str) -> str:
    """Cache key for a full comment tree.

    Example: "comments:tree:uuid-here"
    """
    return f"comments:tree:{root_id}"


def invalidate_list_cache() -> None:
    """Delete all comment list cache entries.

    Called when a new top-level comment is created.
    Uses pattern-based deletion via django-redis.
    """
    from django_redis import get_redis_connection
    redis = get_redis_connection("default")
    # delete all keys matching the list pattern
    pattern = "comments:list:*"
    keys = redis.keys(pattern)
    if keys:
        redis.delete(*keys)


def invalidate_tree_cache(root_id: str) -> None:
    """Delete a specific tree cache entry.

    Called when a reply is added to a thread.
    """
    cache.delete(make_tree_cache_key(root_id))
