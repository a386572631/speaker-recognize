import uuid
import tempfile
import os

from fastapi import APIRouter, Header, HTTPException, Request, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydub import AudioSegment

from ..config import get_settings
from ..services import transcribe_audio, get_last_speaker

router = APIRouter()
settings = get_settings()

ALLOWED_EXTENSIONS = {"mp3", "wav", "ogg", "flac", "m4a", "webm"}


async def verify_auth(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    if token != settings.api_key:
        raise HTTPException(status_code=401, detail="Api Key Error")
    return token


@router.post("/transcriptions")
async def create_transcription(
    request: Request,
    authorization: str = Header(None),
    model: str = Query("whisper-1"),
    response_format: str = Query("json", pattern="^(json|text|srt|verbose_json|vtt)$"),
    language: str = Query(None),
    prompt: str = Query(None),
    temperature: float = Query(0.0, ge=0.0, le=2.0),
):
    await verify_auth(authorization)

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" not in content_type:
        raise HTTPException(
            status_code=400, detail="Content-Type must be multipart/form-data"
        )

    form = await request.form()
    file = form.get("file")

    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")

    filename = file.filename
    if (
        "." not in filename
        or filename.rsplit(".", 1)[1].lower() not in ALLOWED_EXTENSIONS
    ):
        raise HTTPException(status_code=400, detail="Invalid file type")

    unique_filename = f"{uuid.uuid4()}_{filename}"
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, unique_filename)

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        if filename.rsplit(".", 1)[1].lower() == "webm":
            audio = AudioSegment.from_file(temp_path, format="webm")
            audio = audio.set_frame_rate(16000).set_channels(2)
            new_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp3")
            audio.export(new_path, format="mp3")
            os.remove(temp_path)
            temp_path = new_path

        segments = transcribe_audio(temp_path)
        text = " ".join([s["text"] for s in segments])
        total_tokens = len(text) // 4
        duration = segments[-1]["end_time"] if segments else 0

        if response_format == "text":
            text_output = ""
            for segment in segments:
                text_output += f"[{segment['speaker']}]: {segment['text']}\n"
            return PlainTextResponse(content=text_output, media_type="text/plain")

        elif response_format == "verbose_json":
            return JSONResponse(
                content={
                    "task": "transcribe",
                    "language": language or "zh",
                    "duration": duration,
                    "segments": segments,
                    "text": text,
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": total_tokens,
                        "total_tokens": total_tokens,
                    },
                }
            )

        else:
            return JSONResponse(
                content={
                    "text": text,
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": total_tokens,
                        "total_tokens": total_tokens,
                    },
                }
            )

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except:
                pass
