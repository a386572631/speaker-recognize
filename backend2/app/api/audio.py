import base64
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from app.services.asr_service import asr_service
from app.services.tts_service import tts_service
from app.core.config import settings
from app.core.auth import verify_api_key

router = APIRouter()


class TranscriptionResponse(BaseModel):
    text: str


class SpeechRequest(BaseModel):
    input: str
    model: str = "tts-1"
    voice: str = ""


@router.post("/transcription", response_model=TranscriptionResponse)
async def create_transcription(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    model: str = Form(""),
    _: None = Depends(verify_api_key),
):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            if not model:
                model = settings.model

            if "fun-asr" in model.lower():
                text = asr_service.transcribe_fun_asr(tmp_path, language if language != "auto" else None)
            elif "qwen" in model.lower():
                text = asr_service.transcribe_qwen_asr(tmp_path)
            else:
                text = asr_service.transcribe_fun_asr(tmp_path, language if language != "auto" else None)
        finally:
            os.unlink(tmp_path)

        return TranscriptionResponse(text=text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speech")
async def create_speech(request: SpeechRequest, _: None = Depends(verify_api_key)):
    try:
        voice = request.voice if request.voice else settings.tts_voice
        tts_model = settings.tts_model.lower()

        if tts_model == "qwen-tts":
            audio_data = tts_service.synthesize_qwen(request.input, voice)
        else:
            audio_data = await tts_service.synthesize_edge(request.input, voice)

        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))