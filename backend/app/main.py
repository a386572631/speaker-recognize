import torch
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .models import get_asr_model
from .routes import websocket, openai_transcription, transcribe


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"初始化模型: {settings.model_name}, 设备: {settings.device}")
    asr = get_asr_model()
    asr.init()
    yield


app = FastAPI(title="Speaker Recognition API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket.router, tags=["websocket"])
app.include_router(
    openai_transcription.router, prefix="/v1/audio", tags=["openai-transcription"]
)
app.include_router(transcribe.router, prefix="/transcribe", tags=["transcribe"])


@app.get("/health")
async def health_check():
    settings = get_settings()
    asr = get_asr_model()
    if asr.model is None:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": "Model not loaded"},
        )
    return {
        "status": "healthy",
        "model": settings.model_name,
        "device": str(settings.device),
    }
