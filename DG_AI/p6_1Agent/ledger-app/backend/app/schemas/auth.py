from pydantic import BaseModel, ConfigDict

from app.schemas.common import LoginPassword, Nickname, NormalizedEmail, SignupPassword, UtcDateTime


class SignupRequest(BaseModel):
    email: NormalizedEmail
    password: SignupPassword
    nickname: Nickname


class LoginRequest(BaseModel):
    email: NormalizedEmail
    password: LoginPassword


class DeleteAccountRequest(BaseModel):
    password: LoginPassword


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nickname: str
    created_at: UtcDateTime


class AuthResponse(BaseModel):
    user: UserOut
    csrf_token: str
