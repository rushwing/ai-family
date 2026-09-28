"""Independent ChatUI/BFF proof for human confirmation.

The agent receives an OIDC bearer token but never receives the BFF-held HMAC
secret.  A confirmation proof is therefore distinct from ordinary tool auth and
is bound to session, member, tool, payload, timestamp, and a one-time nonce.
"""

from __future__ import annotations

import hashlib
import hmac
import threading
import time

from gateway.confirm import payload_digest


class InteractionProofError(Exception):
    """The request did not prove a fresh user interaction."""


def sign_interaction(
    secret: str,
    *,
    timestamp: int,
    nonce: str,
    session: str,
    member: str,
    tool: str,
    params: dict,
) -> str:
    message = "\n".join(
        (str(timestamp), nonce, session, member, tool, payload_digest(params))
    ).encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


class InteractionVerifier:
    def __init__(
        self, secret: str, *, max_age_seconds: int = 60, max_nonces: int = 10_000
    ) -> None:
        if max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be positive")
        if max_nonces <= 0:
            raise ValueError("max_nonces must be positive")
        self._secret = secret
        self._max_age = max_age_seconds
        self._max_nonces = max_nonces
        self._lock = threading.Lock()
        self._nonces: dict[str, float] = {}

    @property
    def configured(self) -> bool:
        return len(self._secret.encode()) >= 32

    def verify(
        self,
        *,
        timestamp: str | None,
        nonce: str | None,
        signature: str | None,
        session: str,
        member: str,
        tool: str,
        params: dict,
    ) -> None:
        if not self.configured:
            raise InteractionProofError("confirmation channel is not configured")
        if not timestamp or not nonce or not signature:
            raise InteractionProofError("missing interaction proof")
        if not 16 <= len(nonce) <= 128 or len(signature) != 64:
            raise InteractionProofError("malformed interaction proof")
        try:
            issued_at = int(timestamp)
        except ValueError as exc:
            raise InteractionProofError("invalid interaction timestamp") from exc
        now = time.time()
        if abs(now - issued_at) > self._max_age:
            raise InteractionProofError("expired interaction proof")
        expected = sign_interaction(
            self._secret,
            timestamp=issued_at,
            nonce=nonce,
            session=session,
            member=member,
            tool=tool,
            params=params,
        )
        if not hmac.compare_digest(expected, signature):
            raise InteractionProofError("invalid interaction signature")
        with self._lock:
            expired = [
                key for key, seen in self._nonces.items() if now - seen > self._max_age
            ]
            for key in expired:
                self._nonces.pop(key, None)
            if nonce in self._nonces:
                raise InteractionProofError("replayed interaction proof")
            while len(self._nonces) >= self._max_nonces:
                self._nonces.pop(next(iter(self._nonces)))
            self._nonces[nonce] = now
