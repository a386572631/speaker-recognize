from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .models import get_asr_model
from .services import init_hotwords
from .routes import websocket, openai_transcription, transcribe, speech


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_hotwords()
    settings = get_settings()
    print(f"初始化模型: {settings.model_name}, 设备: {settings.device}")
    asr = get_asr_model()
    asr.init()
    print(f"初始化TTS模型: {settings.tts_model}, 设备: {settings.device}")
    from .models import get_tts_model

    tts = get_tts_model()
    tts.init()
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
app.include_router(speech.router, prefix="/v1/audio", tags=["speech"])
app.include_router(transcribe.router, prefix="/transcribe", tags=["transcribe"])


@app.get("/health")
async def health_check():
    from fastapi.responses import JSONResponse

    settings = get_settings()
    asr = get_asr_model()
    settings = get_settings()

    is_loaded = False
    if settings.model_name == "Fun-ASR-Nano-2512":
        is_loaded = asr.funasr_nano_model is not None
    elif settings.model_name.startswith("Qwen"):
        is_loaded = asr.qwen_model is not None

    if not is_loaded:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "message": "Model not loaded"},
        )
    return {
        "status": "healthy",
        "model": settings.model_name,
        "device": str(settings.device),
    }
