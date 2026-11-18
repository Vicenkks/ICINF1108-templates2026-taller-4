from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth.schemas import (
    ForgotPasswordDto,
    ForgotPasswordResponse,
    LoginDto,
    RegisterDto,
    ResetPasswordDto,
    User,
)
from app.auth.service import UNAUTHORIZED_MESSAGE, AuthServiceDep
from app.auth.session import (
    CurrentSession,
    clear_session_cookie,
    session_cookie,
    set_session_cookie,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

SessionCookie = Annotated[str | None, Depends(session_cookie)]


# Crea la cuenta e inicia sesión de inmediato.
@router.post("/register", status_code=201)
def register(
    body: RegisterDto,
    response: Response,
    service: AuthServiceDep,
    session_id: SessionCookie,
) -> User:
    user = service.register(body)
    new_session_id = service.start_session(user.id, session_id)
    set_session_cookie(response, new_session_id)
    return user


@router.post("/login")
def login(
    body: LoginDto,
    response: Response,
    service: AuthServiceDep,
    session_id: SessionCookie,
) -> User:
    user = service.login(body)
    new_session_id = service.start_session(user.id, session_id)
    set_session_cookie(response, new_session_id)
    return user


@router.post("/logout")
def logout(
    response: Response, service: AuthServiceDep, session_id: SessionCookie
) -> None:
    service.destroy_session(session_id)
    clear_session_cookie(response)


@router.post("/password/forgot")
def forgot_password(
    body: ForgotPasswordDto, request: Request, service: AuthServiceDep
) -> ForgotPasswordResponse:
    reset_link = service.forgot_password(body, str(request.base_url))
    return ForgotPasswordResponse(reset_link=reset_link)


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(body: ResetPasswordDto, service: AuthServiceDep) -> Response:
    service.reset_password(body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me")
def me(session: CurrentSession, response: Response, service: AuthServiceDep) -> User:
    user = service.find_user(session.userId)

    # La sesión apunta a un usuario que ya no existe.
    if user is None:
        service.destroy_session(session.id)
        clear_session_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=UNAUTHORIZED_MESSAGE
        )

    return user
