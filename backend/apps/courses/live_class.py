"""Who may enter a live class, and the pass Jitsi checks at the door.

Two modes, picked by settings (JITSI_* in config/settings/base.py):
- public meet.jit.si (no JITSI_APP_SECRET): the room's unguessable name, handed out only by
  ClassSessionViewSet.join, is the only lock;
- self-hosted Jitsi with JWT auth (deploy/JITSI_SETUP.md): every entry also needs a short-lived
  token signed with JITSI_APP_SECRET, valid for that one room and this one person. A room name
  passed around is useless without it, and the instructor enters as moderator.
"""
from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone

# Jitsi checks the token when someone enters, not during the call: an hour to click through.
TOKEN_LIFETIME = timedelta(hours=1)


def uses_tokens() -> bool:
    return bool(settings.JITSI_APP_SECRET)


def room_name(session) -> str:
    # Jitsi lower-cases room names; the token's "room" must match what it compares against.
    return session.room_slug.lower()


def entry_token(session, user, *, moderator: bool) -> str:
    now = timezone.now()
    claims = {
        "aud": "jitsi",
        "iss": settings.JITSI_APP_ID,
        "sub": settings.JITSI_DOMAIN,
        "room": room_name(session),
        "iat": int(now.timestamp()),
        "nbf": int((now - timedelta(minutes=1)).timestamp()),
        "exp": int((now + TOKEN_LIFETIME).timestamp()),
        "moderator": moderator,
        "context": {"user": {
            "id": str(user.id),
            "name": user.get_full_name() or user.email.split("@")[0],
            "moderator": moderator,
            "affiliation": "owner" if moderator else "member",
        }},
    }
    return jwt.encode(claims, settings.JITSI_APP_SECRET, algorithm="HS256")


def join_details(session, user, *, moderator: bool) -> dict:
    details = {
        "domain": settings.JITSI_DOMAIN,
        "room_name": room_name(session) if uses_tokens() else session.room_slug,
        "display_name": user.get_full_name() or user.email,
        "title": session.title,
        "course_title": session.course.title,
    }
    if uses_tokens():
        details["jwt"] = entry_token(session, user, moderator=moderator)
    return details
