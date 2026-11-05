"""
Usage limits for LLM calls on the public deployment.

Two layers:
  1. Per-session limit  — stops one visitor from spamming the buttons.
  2. Global daily limit — caps total OpenAI calls per day across all visitors
     (shared in-process via st.cache_resource; resets at UTC midnight or on app restart).

Limits can be overridden via env vars / Streamlit Secrets without code changes.
"""
import threading
from datetime import datetime, timezone

import streamlit as st

from src.config.settings import _get_secret


def _int_setting(key: str, default: int) -> int:
    try:
        return int(_get_secret(key) or default)
    except (TypeError, ValueError):
        return default


# kind -> (per-session limit, global daily limit)
LIMITS = {
    "analyze": (_int_setting("LIMIT_ANALYZE_SESSION", 5),  _int_setting("LIMIT_ANALYZE_DAILY", 100)),
    "report":  (_int_setting("LIMIT_REPORT_SESSION", 3),   _int_setting("LIMIT_REPORT_DAILY", 50)),
    "chat":    (_int_setting("LIMIT_CHAT_SESSION", 20),    _int_setting("LIMIT_CHAT_DAILY", 300)),
}

_LABELS = {"analyze": "AI analyses", "report": "report generations", "chat": "chat messages"}


@st.cache_resource
def _global_counter() -> dict:
    return {"date": None, "counts": {}, "lock": threading.Lock()}


def try_consume(kind: str) -> bool:
    """Return True and count one use if under both limits; otherwise show a warning and return False."""
    session_limit, daily_limit = LIMITS[kind]
    label = _LABELS.get(kind, kind)

    used = st.session_state.setdefault("_usage_counts", {}).get(kind, 0)
    if used >= session_limit:
        st.warning(f"You've reached the limit of {session_limit} {label} for this session. "
                   "Thanks for trying Solomon!")
        return False

    g = _global_counter()
    today = datetime.now(timezone.utc).date().isoformat()
    with g["lock"]:
        if g["date"] != today:
            g["date"], g["counts"] = today, {}
        if g["counts"].get(kind, 0) >= daily_limit:
            st.warning(f"Solomon has hit today's limit for {label}. Please come back tomorrow.")
            return False
        g["counts"][kind] = g["counts"].get(kind, 0) + 1

    st.session_state["_usage_counts"][kind] = used + 1
    return True
