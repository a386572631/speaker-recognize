import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

for logger_name in ["funasr", "modelscope", " transformers", "urllib3"]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

app = FastAPI(
    title="Speaker Recognition API",
    description="OpenAI-compatible API for speaker recognition and audio transcription",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import audio, transcribe
from app.api.websocket import router as websocket_router

app.include_router(audio.router, prefix="/v1/audio", tags=["audio"])
app.include_router(websocket_router, prefix="/ws", tags=["websocket"])
app.include_router(transcribe.router, tags=["transcribe"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}