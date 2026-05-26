from typing import Literal

from pydantic import BaseModel, Field


class ChatHistoryMessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatQueryCreate(BaseModel):
    pregunta: str = Field(min_length=1, max_length=1000)
    material_id: int | None = Field(default=None, ge=1)
    horizonte_meses: int = Field(default=3, ge=1, le=12)
    historial: list[ChatHistoryMessageCreate] = Field(default_factory=list, max_length=8)


class ChatResponseRead(BaseModel):
    aceptada: bool
    respuesta: str
    proveedor_utilizado: bool
