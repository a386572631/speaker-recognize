from pydantic import BaseModel
from typing import Optional


class TranscriptionRequest(BaseModel):
    audio: str
    model: Optional[str] = None


class TranscriptionResponse(BaseModel):
    segments: list
    last_speaker: str


class WebSocketMessage(BaseModel):
    type: str
    audio: Optional[str] = None
    isFinal: Optional[bool] = None


class WebSocketResponse(BaseModel):
    status: Optional[str] = None
    result: Optional[list] = None
    error: Optional[str] = None
