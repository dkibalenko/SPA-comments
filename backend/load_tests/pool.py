"""Thread-safe pool of comment IDs discovered during the load test.

PostingUser and ReplyingUser register every successfully created comment.
ReadingUser and ReplyingUser draw random IDs from the pool to call
the tree endpoint or to pick a parent for a reply.
"""

import random
import threading


# all Locust user threads share the same pool
_ids: list[str] = []  # single global list
_lock = threading.Lock()  # single global lock

POOL_MAX = 500


def register(cid: str) -> None:
    """Add a comment ID. Evicts the oldest entry when POOL_MAX is reached."""
    with _lock:
        _ids.append(cid)
        if len(_ids) > POOL_MAX:
            _ids.pop(0)


def pick() -> str | None:
    """Return a random comment ID, or None if the pool is empty."""
    with _lock:
        return random.choice(_ids) if _ids else None


def seed(client) -> None:
    """Populate the pool from the first page of existing comments.

    Called by each user's `on_start` so tree and reply tasks have real IDs
    to work with before any new comments have been created by the test.

    This runs immediately when a user spawns, before any tasks execute
    """
    # fetch the first page of comments
    resp = client.get(
        "/api/comments/?ordering=-date&page=1",
        name="/api/comments/ [seed]",
    )
    if resp.status_code != 200:
        return
    # extracts IDs
    for item in resp.json().get("results", []):
        cid = item.get("id")
        if cid:
            # register IDs into the pool
            register(cid)
