from typing import Annotated

from fastapi import Depends, Response
from fastapi.security import APIKeyCookie

from app.auth.models import UserSessionModel
from app.auth.service import AuthServiceDep
from app.shared.config import (
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
    SESSION_MAX_AGE_SECONDS,
)

# Lee la cookie `sid`. Además agrega el botón "Authorize" en /docs.
session_cookie = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=SESSION_COOKIE_SECURE,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME)


def require_session(
    service: AuthServiceDep,
    session_id: Annotated[str | None, Depends(session_cookie)],
) -> UserSessionModel:
    return service.require_session(session_id)


CurrentSession = Annotated[UserSessionModel, Depends(require_session)]
