import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import streamlit as st
from dotenv import load_dotenv
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from streamlit_cookies_controller.cookie_controller import _cookie_controller

load_dotenv()

COOKIE_NAME = "pogo_auth"
COOKIE_DAYS = int(os.getenv("AUTH_COOKIE_DAYS", "14"))
_AUTH_SECRET = os.getenv("AUTH_SECRET")
_COOKIE_SYNC_SECONDS = 0.5


def _serializer() -> URLSafeTimedSerializer:
    if not _AUTH_SECRET:
        raise RuntimeError(
            "AUTH_SECRET is missing. Add it to your .env file "
            "(see README / setup notes)."
        )
    return URLSafeTimedSerializer(_AUTH_SECRET, salt="pogo-auth")


def make_token(user_id: int, username: str) -> str:
    return _serializer().dumps({"id": user_id, "username": username})


def parse_token(token: str) -> dict | None:
    if not token:
        return None
    try:
        data = _serializer().loads(token, max_age=COOKIE_DAYS * 86400)
        user_id = int(data["id"])
        username = str(data["username"])
        if not username:
            return None
        return {"id": user_id, "username": username}
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        return None


def _cookie_options(
    *,
    expires: datetime,
    max_age: float,
    path: str = "/",
    same_site: str = "lax",
) -> dict:
    return {
        "path": path,
        "expires": expires.isoformat(),
        "maxAge": max_age,
        "sameSite": same_site,
    }


def _write_cookie(value: str, *, expires: datetime, max_age: float) -> None:
    # Unique widget key each call avoids Streamlit session_state lock conflicts
    # from CookieController's stable key="pogo_cookies".
    _cookie_controller(
        method="set",
        name=COOKIE_NAME,
        value=value,
        options=_cookie_options(expires=expires, max_age=max_age),
        key=f"pogo_auth_cookie_{uuid.uuid4().hex}",
    )


def restore_user() -> None:
    if "user" in st.session_state:
        return

    # After logout in this browser session, never resurrect from a stale cookie
    # still present in st.context.cookies until the next successful login.
    if st.session_state.get("auth_logged_out"):
        return

    user = parse_token(st.context.cookies.get(COOKIE_NAME))
    if user:
        st.session_state["user"] = user


def persist_login(user_id: int, username: str) -> None:
    token = make_token(user_id, username)
    st.session_state.pop("auth_logged_out", None)
    st.session_state["user"] = {"id": user_id, "username": username}
    _write_cookie(
        token,
        expires=datetime.now() + timedelta(days=COOKIE_DAYS),
        max_age=COOKIE_DAYS * 86400,
    )
    time.sleep(_COOKIE_SYNC_SECONDS)


def clear_login() -> None:
    """Clear session auth and expire the browser cookie."""
    st.session_state.clear()
    st.session_state["auth_logged_out"] = True
    st.session_state.pop("user", None)
    st.query_params.clear()

    _write_cookie(
        "",
        expires=datetime.now(timezone.utc) - timedelta(days=1),
        max_age=0,
    )
    time.sleep(_COOKIE_SYNC_SECONDS)
