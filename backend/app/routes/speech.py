import os
import tempfile

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import Response

import soundfile as sf

from ..auth import verify_auth
from ..config import get_settings

router = APIRouter()


@router.post("/speech")
async def create_speech(
    request: Request,
    authorization: str = Header(None),
    model: str = Query("tts-1"),
    voice: str = Query(None),
    response_format: str = Query("mp3", pattern="^(mp3|wav|opus)$"),
    speed: float = Query(1.0, ge=0.25, le=4.0),
):
    await verify_auth(authorization)

    from ..models import get_tts_model

    tts = get_tts_model()

    body = await request.json()

    if "input" not in body:
        raise HTTPException(status_code=400, detail="Missing 'input' field")

    text = body["input"]
    settings = get_settings()
    speaker = body.get("voice") or voice or settings.tts_voice

    if tts.tts_type == "qwen":
        instruct = body.get(
            "instruct", "用平和的语气说，并充分理解文本中的数字，尤其是身份证号"
        )
        wavs, sr = tts.generate_custom_voice(
            text=text,
            language="Chinese",
            speaker=speaker,
            instruct=instruct,
        )
    else:
        wavs, sr = await tts.generate_custom_voice_async(
            text=text,
            voice=speaker,
            speed=speed,
        )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        sf.write(tmp.name, wavs[0], sr)
        with open(tmp.name, "rb") as f:
            audio_data = f.read()
        os.unlink(tmp.name)

    media_type = "audio/mpeg" if response_format == "mp3" else "audio/wav"
    return Response(content=audio_data, media_type=media_type)
