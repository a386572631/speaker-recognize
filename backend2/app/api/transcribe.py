import logging
import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Form
from pydantic import BaseModel
from app.core.auth import verify_api_key
from app.core.config import settings
from app.services.asr_service import asr_service
from app.services.diarization_service import diarization_service

router = APIRouter()
logger = logging.getLogger(__name__)

class TranscriptionResult(BaseModel):
    text: str
    segments: list = []


def merge_asr_and_speaker(timestamps, speaker_segments):
    if not timestamps:
        return []

    merged = []
    for ts in timestamps:
        if hasattr(ts, "text"):
            token = ts.text
            start = ts.start_time
            end = ts.end_time
        else:
            token = ts["token"]
            start = ts["start_time"]
            end = ts["end_time"]

        speaker = "SPEAKER_UNKNOWN"
        for seg in speaker_segments:
            if start >= seg["start"] and start < seg["end"]:
                speaker = seg["speaker"]
                break
            elif start < seg["start"] and end > seg["start"]:
                speaker = seg["speaker"]
                break

        merged.append({
            "token": token,
            "start": start,
            "end": end,
            "speaker": speaker
        })

    result = []
    if merged:
        current = {
            "text": merged[0]["token"],
            "start": merged[0]["start"],
            "end": merged[0]["end"],
            "speaker": merged[0]["speaker"]
        }

        for item in merged[1:]:
            if item["speaker"] == current["speaker"]:
                current["text"] += item["token"]
                current["end"] = item["end"]
            else:
                result.append(current)
                current = {
                    "text": item["token"],
                    "start_time": item["start"],
                    "end_time": item["end"],
                    "speaker": item["speaker"]
                }
        result.append(current)

    return result


@router.post("/transcribe", response_model=TranscriptionResult)
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form(""),
    language: str = Form("auto"),
    num_speakers: int = Query(0),
    _: None = Depends(verify_api_key)
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
                asr_result = asr_service.fun_asr.generate(
                    input=[tmp_path],
                    language="auto",
                    itn=True,
                )
                full_text = asr_result[0].get("text", "")
                timestamps = asr_result[0].get("timestamps", [])
            elif "qwen" in model.lower():
                asr_result = asr_service.qwen_asr.transcribe(
                    audio=[tmp_path],
                    language="Chinese",
                    return_time_stamps=True,
                    # context=hotwords,
                )
                full_text = asr_result[0].text
                timestamps = asr_result[0].time_stamps.items
            else:
                asr_result = asr_service.fun_asr.generate(
                    input=[tmp_path],
                    language="auto",
                    itn=True,
                )
                full_text = asr_result[0].get("text", "")
                timestamps = asr_result[0].get("timestamps", [])
            
            logger.info("每个字的timestamp：" + str(timestamps))
            speaker_segments = diarization_service.diarize(tmp_path, num_speakers)
            logger.info("说话人聚类结果：" + str(speaker_segments))
            merged_segments = merge_asr_and_speaker(timestamps, speaker_segments)

            return TranscriptionResult(
                text=full_text,
                segments=merged_segments
            )
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))