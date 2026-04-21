import io
import tempfile
import os
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.asr_service import asr_service
from app.core.config import settings

router = APIRouter()


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
                    if token != f"Bearer {settings.openai_api_key}":
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
                    import base64
                    audio_bytes = base64.b64decode(audio_base64)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                        tmp.write(audio_bytes)
                        tmp_path = tmp.name

                    try:
                        if "fun-asr" in settings.model.lower():
                            text = asr_service.transcribe_fun_asr(tmp_path)
                        elif "qwen" in settings.model.lower():
                            text = asr_service.transcribe_qwen_asr(tmp_path)
                        else:
                            text = asr_service.transcribe_fun_asr(tmp_path)
                    finally:
                        os.unlink(tmp_path)

                    await websocket.send_json({"result": text})

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await websocket.send_json({"error": f"Transcription failed: {str(e)}"})

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