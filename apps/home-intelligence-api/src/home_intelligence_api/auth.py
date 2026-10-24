"""Pinned OIDC RSA verification; never resolve URLs or trust identity headers."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, NoReturn

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey

_ROLES = {
    "admin": "admin",
    "adult": "adult",
    "kid": "kid",
    "best_pal": "admin",
    "go_getter": "adult",
}


class AuthenticationError(Exception):
    def __init__(self) -> None:
        super().__init__("unauthenticated")


class RoleError(Exception):
    def __init__(self) -> None:
        super().__init__("forbidden")


@dataclass(frozen=True, slots=True, repr=False)
class Identity:
    subject_id: str
    family_member_id: str
    role: str

    def context(self, home_id: str) -> dict[str, str]:
        return {
            "subject_id": self.subject_id,
            "family_member_id": self.family_member_id,
            "role": self.role,
            "home_id": home_id,
        }

    def __repr__(self) -> str:
        return "Identity(<redacted>)"


@dataclass(frozen=True, slots=True, repr=False, init=False)
class TokenVerifier:
    """Immutable trusted config. Recompose the app to rotate keys or revoke grants.

    Follows gateway role aliases/conflict behavior without importing Goal tooling
    or using its global environment and network JWKS cache.
    """

    _issuer: str
    _audience: str
    _keys: Mapping[str, RSAPublicKey]

    def __init__(self, *, issuer: str, audience: str, public_keys: Mapping[str, bytes]):
        if hasattr(self, "_keys"):
            raise ValueError("immutable_verifier")
        failed = False
        keys: dict[str, RSAPublicKey] = {}
        try:
            if (
                type(issuer) is not str
                or not issuer.startswith("https://")
                or issuer != issuer.strip()
                or len(issuer) > 2048
                or type(audience) is not str
                or not audience.strip()
                or audience != audience.strip()
                or len(audience) > 256
                or not public_keys
                or len(public_keys) > 16
            ):
                raise ValueError()
            for kid, pem in public_keys.items():
                if (
                    type(kid) is not str
                    or not kid
                    or len(kid) > 128
                    or type(pem) is not bytes
                    or len(pem) > 16384
                ):
                    raise ValueError()
                key = serialization.load_pem_public_key(pem)
                if not isinstance(key, RSAPublicKey) or key.key_size < 2048:
                    raise ValueError()
                keys[kid] = key
        except Exception:
            failed = True
        if failed:
            raise ValueError("invalid_auth_configuration")
        object.__setattr__(self, "_issuer", issuer)
        object.__setattr__(self, "_audience", audience)
        object.__setattr__(self, "_keys", MappingProxyType(keys))

    def __repr__(self) -> str:
        return "TokenVerifier(<redacted>)"

    def __reduce__(self) -> NoReturn:
        raise TypeError("verifier_serialization_forbidden")

    def verify(self, token: str) -> Identity:
        failed = False
        identity: Identity | None = None
        role_denied = False
        try:
            if type(token) is not str or not token or len(token) > 16384:
                raise ValueError()
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or header.get("crit"):
                raise ValueError()
            kid = header.get("kid")
            if type(kid) is not str or kid not in self._keys:
                raise ValueError()
            claims = jwt.decode(
                token,
                self._keys[kid],
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={
                    "require": ["exp", "iat", "sub", "aud", "iss", "family_member_id"],
                    "strict_aud": True,
                },
            )
            if any(type(claims[k]) is not int for k in ("iat", "exp")):
                raise ValueError()
            if claims["exp"] <= claims["iat"]:
                raise ValueError()
            if "nbf" in claims and type(claims["nbf"]) is not int:
                raise ValueError()
            for name in ("sub", "family_member_id"):
                value = claims[name]
                if (
                    type(value) is not str
                    or not value.strip()
                    or value != value.strip()
                    or len(value) > 256
                ):
                    raise ValueError()
            raw_role = claims.get("role")
            realm = claims.get("realm_access", {})
            if type(realm) is not dict:
                raise ValueError()
            roles = realm.get("roles", [])
            if type(roles) is not list or any(type(r) is not str for r in roles):
                raise ValueError()
            if raw_role is not None:
                if type(raw_role) is not str:
                    raise ValueError()
                roles = [*roles, raw_role]
            mapped = {_ROLES[r] for r in roles if r in _ROLES}
            if len(mapped) != 1:
                role_denied = True
            else:
                identity = Identity(claims["sub"], claims["family_member_id"], mapped.pop())
        except Exception:
            failed = True
        # Raise outside the parsing handler to avoid retaining token-bearing chains.
        if failed:
            raise AuthenticationError()
        if role_denied:
            raise RoleError()
        if identity is None:
            raise AuthenticationError()
        return identity
