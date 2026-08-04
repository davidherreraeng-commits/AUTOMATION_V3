from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from domain.models.user_account import UserAccount
from infrastructure.config.settings import Settings


class InvalidAccessTokenError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AccessToken:
    value: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: int
    username: str
    dependency: str
    role: str
    expires_at: datetime


class JWTService:
    """Emite y valida tokens de acceso de la herramienta."""

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.jwt_secret_key.get_secret_value()
        self._algorithm = settings.jwt_algorithm
        self._issuer = settings.jwt_issuer
        self._audience = settings.jwt_audience
        self._duration = timedelta(
            minutes=settings.access_token_minutes
        )

    def create_access_token(self, user: UserAccount) -> AccessToken:
        now = datetime.now(timezone.utc)
        expires_at = now + self._duration
        payload = {
            "sub": user.username,
            "uid": user.user_id,
            "dep": user.dependency,
            "role": user.role.value,
            "type": "access",
            "jti": str(uuid4()),
            "iat": now,
            "exp": expires_at,
            "iss": self._issuer,
            "aud": self._audience,
        }
        encoded = jwt.encode(
            payload,
            self._secret,
            algorithm=self._algorithm,
        )
        return AccessToken(value=encoded, expires_at=expires_at)

    def decode_access_token(self, token: str) -> AccessTokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["sub", "uid", "exp", "type"]},
            )
        except jwt.PyJWTError as error:
            raise InvalidAccessTokenError() from error

        if payload.get("type") != "access":
            raise InvalidAccessTokenError()

        try:
            expires_at = datetime.fromtimestamp(
                int(payload["exp"]),
                tz=timezone.utc,
            )
            return AccessTokenClaims(
                user_id=int(payload["uid"]),
                username=str(payload["sub"]),
                dependency=str(payload.get("dep", "")),
                role=str(payload.get("role", "")),
                expires_at=expires_at,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise InvalidAccessTokenError() from error
