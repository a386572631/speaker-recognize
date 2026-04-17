import json
import os
import tempfile

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Header, HTTPException

from ..config import get_settings
from ..services import transcribe_audio_base64

router = APIRouter()
settings = get_settings()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        auth_received = False
        while True:
            data = await websocket.receive_text()

            if not auth_received:
                if data.startswith("Authorization:"):
                    token = data.split(":", 1)[1].strip()
                    if token != f"Bearer {settings.api_key}":
                        await websocket.send_json({"error": "Api Key Error"})
                        await websocket.close()
                        return
                    auth_received = True
                    await websocket.send_json({"status": "connected"})
                continue

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            if message.get("type") == "transcribe":
                audio_base64 = message.get("audio", "")
                if not audio_base64:
                    await websocket.send_json({"error": "No audio data"})
                    continue

                await websocket.send_json({"status": "Processing audio..."})

                try:
                    segments = transcribe_audio_base64(
                        audio_base64, use_diarization=False
                    )
                    await websocket.send_json({"result": segments})

                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    await websocket.send_json(
                        {"error": f"Transcription failed: {str(e)}"}
                    )

            elif message.get("type") == "ping":
                await websocket.send_json({"status": "pong"})

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
