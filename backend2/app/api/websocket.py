import io
import tempfile
import os
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.asr_service import asr_service
from app.core.config import settings

router = APIRouter()


@router.websocket("/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    model = settings.model
    await websocket.accept()

    try:
        config_msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
        config = json.loads(config_msg)
        if config.get("model"):
            model = config["model"]
            await websocket.send_json({"type": "config", "model": model, "status": "ok"})
    except:
        await websocket.send_json({"type": "config", "model": model, "status": "ok"})

    buffer = b""

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_bytes(), timeout=10.0)
            except asyncio.TimeoutError:
                if buffer:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                        tmp.write(buffer)
                        tmp_path = tmp.name

                    try:
                        if "fun-asr" in model.lower():
                            text = asr_service.transcribe_fun_asr(tmp_path)
                        elif "qwen" in model.lower():
                            text = asr_service.transcribe_qwen_asr(tmp_path)
                        else:
                            text = asr_service.transcribe_fun_asr(tmp_path)
                    finally:
                        os.unlink(tmp_path)

                    await websocket.send_json({
                        "type": "transcription",
                        "text": text,
                        "status": "completed"
                    })
                    buffer = b""
                continue

            buffer += data

            if len(buffer) > 1024 * 1024:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    tmp.write(buffer)
                    tmp_path = tmp.name

                try:
                    if "fun-asr" in model.lower():
                        text = asr_service.transcribe_fun_asr(tmp_path)
                    elif "qwen" in model.lower():
                        text = asr_service.transcribe_qwen_asr(tmp_path)
                    else:
                        text = asr_service.transcribe_fun_asr(tmp_path)
                finally:
                    os.unlink(tmp_path)

                await websocket.send_json({
                    "type": "transcription",
                    "text": text,
                    "status": "completed"
                })
                buffer = b""

    except WebSocketDisconnect:
        pass