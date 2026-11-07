"""Notification channel (FR-6.6, decision D5): an interface plus a log-only sender for development."""
import logging
from typing import Protocol

log = logging.getLogger("talenthub.notifications")


class Notifier(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class LogNotifier:
    def send(self, to: str, subject: str, body: str) -> None:
        log.info("mail to=%s subject=%s", to, subject)


def get_notifier() -> Notifier:
    return LogNotifier()
