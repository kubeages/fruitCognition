from __future__ import annotations

import threading
from typing import Protocol

from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract


class CognitionFabric(Protocol):
    """Storage interface shared by the in-memory and (later) Postgres backends."""

    def save_intent(self, intent: IntentContract) -> None: ...
    def get_intent(self, intent_id: str) -> IntentContract | None: ...
    def list_intents(self) -> list[IntentContract]: ...
    def save_claim(self, claim: Claim) -> None: ...
    def list_claims(self, intent_id: str) -> list[Claim]: ...


class InMemoryCognitionFabric:
    """Process-local cognition store. Lost on restart — see SPEC iter 16 for Postgres."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.intents: dict[str, IntentContract] = {}
        self.claims: dict[str, list[Claim]] = {}

    def save_intent(self, intent: IntentContract) -> None:
        with self._lock:
            self.intents[intent.intent_id] = intent

    def get_intent(self, intent_id: str) -> IntentContract | None:
        with self._lock:
            return self.intents.get(intent_id)

    def list_intents(self) -> list[IntentContract]:
        with self._lock:
            return list(self.intents.values())

    def save_claim(self, claim: Claim) -> None:
        with self._lock:
            self.claims.setdefault(claim.intent_id, []).append(claim)

    def list_claims(self, intent_id: str) -> list[Claim]:
        with self._lock:
            return list(self.claims.get(intent_id, []))


_singleton: InMemoryCognitionFabric | None = None
_singleton_lock = threading.Lock()


def get_fabric() -> InMemoryCognitionFabric:
    """Return the process-wide cognition fabric, creating it on first access."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = InMemoryCognitionFabric()
    return _singleton


def reset_fabric() -> None:
    """Drop the singleton — for tests only."""
    global _singleton
    with _singleton_lock:
        _singleton = None
