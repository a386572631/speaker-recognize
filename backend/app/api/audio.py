import base64
import tempfile
import os
import io
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from fastapi.responses import Response, StreamingResponse
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


@router.post("/transcriptions", response_model=TranscriptionResponse)
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
        audio_data = tts_service.synthesize(request.input, request.voice)

        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speechStream")
async def create_speech_stream(request: SpeechRequest, _: None = Depends(verify_api_key)):
    try:
        #def generate():
        #    for chunk in tts_service.synthesize_cosyvoice_stream(request.input, request.voice):
        #        yield chunk

        #return StreamingResponse(
        #    generate(),
        #    media_type="audio/wav",
        #    headers={"Content-Disposition": "attachment; filename=speech.wav"},
        #)
        def generate():
            for pcm_chunk in tts_service.synthesize_cosyvoice_stream(
                request.input, request.voice
            ):
                yield pcm_chunk

        return StreamingResponse(
            generate(),
            media_type="audio/L16",
            headers={
                "X-Sample-Rate": str(tts_service._cosyvoice_model.sample_rate),
                "X-Channels": "1",
                "X-Bits": "16",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

