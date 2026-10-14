"""A per-conversation change counter, so an idle chat poll costs no queries.

Every write that changes what a poll would return (messages, edits and
deletions, reactions, read receipts, members, settings) bumps the counter.
A poll that sends the version it last saw and finds it unchanged gets an
empty answer instead of the full message/marker/row queries.

Lives in the cache (Redis in production, shared by every gunicorn worker).
Losing a key is harmless: it comes back as a new value, which only costs
each open chat one full poll.
"""
import time

from django.core.cache import cache
from django.db import transaction

# Long enough to matter, short enough that Redis may evict it under memory pressure (volatile-lru).
TTL_SECONDS = 24 * 60 * 60


def _key(conversation_id: int) -> str:
    return f"chat:v:{conversation_id}"


def _fresh() -> int:
    # Time-based, so a recreated key never equals a version a client still holds.
    return time.time_ns() // 1000


def current(conversation_id: int) -> int:
    key = _key(conversation_id)
    version = cache.get(key)
    if version is None:
        version = _fresh()
        if not cache.add(key, version, TTL_SECONDS):
            version = cache.get(key, version)  # another request created it first
    return int(version)


def _bump_now(conversation_id: int) -> None:
    key = _key(conversation_id)
    try:
        cache.incr(key)
    except ValueError:  # missing: start over from a value no client has seen
        cache.set(key, _fresh(), TTL_SECONDS)


def bump(conversation_id: int | None) -> None:
    """Mark the conversation changed once the current transaction commits.

    Bumping before the commit would let a poll see the new version, query
    before the row is visible, and then never ask again.
    """
    if conversation_id:
        transaction.on_commit(lambda: _bump_now(conversation_id))
