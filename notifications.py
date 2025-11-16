"""Deprecated module.

Use core.notification_service.NotificationService instead.
This file remains to avoid breaking imports; it re-exports a compatible facade.
"""

from __future__ import annotations
from core.notification_service import NotificationService  # type: ignore


def send_email_alert(subject: str, message: str, recipient: str | None = None):
    try:
        svc = NotificationService()
        svc.send_email(subject, message, to_addr=recipient)
    except Exception:
        # Best-effort backward compatibility; ignore failures here.
        pass
