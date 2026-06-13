from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    nombre: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=8, max_length=200)


class PasswordRecoveryRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=160)


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=1, max_length=2000)
    password: str = Field(min_length=8, max_length=200)


class MessageResponse(BaseModel):
    message: str


class UsuarioRead(BaseModel):
    id: int
    username: str
    email: str | None = None
    nombre: str
    rol: str

    model_config = ConfigDict(from_attributes=True)


class UsuarioAdminRead(BaseModel):
    id: int
    username: str
    email: str | None = None
    nombre: str
    rol: str
    activo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    usuario: UsuarioRead


class RegisterResponse(BaseModel):
    message: str
    usuario: UsuarioRead
