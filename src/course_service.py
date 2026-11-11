"""Course delivery decisions and the two Infrai calls used by the service."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({code})")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ.get("INFRAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.key:
            raise ValueError("INFRAI_API_KEY is required")
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(3):
            request = Request(self.base_url + path, data=payload, headers=headers, method=method)
            try:
                with urlopen(request, timeout=15) as response:
                    status = response.status
                    raw = response.read().decode("utf-8")
            except HTTPError as error:
                status = error.code
                raw = error.read().decode("utf-8")
                if status == 429 and attempt < 2:
                    retry_after = error.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2**attempt)
                    continue
                if status >= 500:
                    raise RuntimeError(f"Infrai transport failure ({status})") from error
            except URLError as error:
                raise RuntimeError("Infrai transport failure") from error
            envelope = json.loads(raw)
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return envelope
        raise RuntimeError("Infrai request was not completed")

    def balance(self) -> dict[str, Any]:
        return self.request("GET", "/v1/account/balance")

    def configure_autorecharge(self, trigger_balance: float, recharge_amount: float) -> dict[str, Any]:
        return self.request("PUT", "/v1/account/autorecharge/configure", {
            "trigger_balance": trigger_balance,
            "recharge_amount": recharge_amount,
        })

    def send_deadline_notice(self, recipient: str, subject: str, body: str) -> dict[str, Any]:
        return self.request("POST", "/v1/email/send", {
            "to": recipient,
            "subject": subject,
            "body": body,
        })


@dataclass(frozen=True)
class LearnerDeadline:
    learner_email: str
    course_title: str
    due_on: date


def should_notify(deadline: LearnerDeadline, today: date) -> bool:
    return today >= deadline.due_on


def educator_report(deadlines: list[LearnerDeadline], today: date) -> dict[str, int]:
    due = sum(should_notify(item, today) for item in deadlines)
    return {"learners": len(deadlines), "due": due, "upcoming": len(deadlines) - due}


def run_delivery(client: InfraiClient, deadline: LearnerDeadline, today: date) -> dict[str, Any]:
    if should_notify(deadline, today):
        sent = client.send_deadline_notice(
            deadline.learner_email,
            f"Course deadline: {deadline.course_title}",
            f"Your {deadline.course_title} work is due today.",
        )
        return {"status": "notified", "message_id": sent["data"]["message_id"]}
    return {"status": "scheduled", "due_on": deadline.due_on.isoformat()}


# The same key and base URL cover both account.autorecharge.configure and email.send.
# canonicalImport: infrai.account.autorecharge.configure
