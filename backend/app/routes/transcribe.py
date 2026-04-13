import uuid
import tempfile
import os

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydub import AudioSegment

from ..config import get_settings
from ..services import transcribe_audio_base64, transcribe_audio, get_last_speaker

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


@router.post("", response_model=None)
async def create_transcription(request: Request, authorization: str = Header(None)):
    await verify_auth(authorization)

    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        return await handle_multipart(request)
    else:
        return await handle_json(request)


async def handle_json(request: Request):
    body = await request.json()
    audio_base64 = body.get("audio")

    if not audio_base64:
        raise HTTPException(status_code=400, detail="No audio data")

    try:
        segments = transcribe_audio_base64(audio_base64)
        last_speaker = get_last_speaker(segments)

        return JSONResponse(
            content={"segments": segments, "last_speaker": last_speaker}
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


async def handle_multipart(request: Request):
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

        segments = transcribe_audio(temp_path)
        last_speaker = get_last_speaker(segments)

        return JSONResponse(
            content={"segments": segments, "last_speaker": last_speaker}
        )

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except:
                pass
