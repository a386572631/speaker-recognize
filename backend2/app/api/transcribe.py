import logging
import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Form
from pydantic import BaseModel
from app.core.auth import verify_api_key
from app.core.config import settings
from app.services.asr_service import asr_service
from app.services.diarization_service import diarization_service
from app.services.speaker_verify_service import speaker_verify_service

router = APIRouter()
logger = logging.getLogger(__name__)


class TranscriptionResult(BaseModel):
    text: str
    last_speaker: str = None
    segments: list = []
    spk_embedding: list = None


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
        similarity = None
        segment_start = None
        segment_end = None

        for seg in speaker_segments:
            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", float("inf"))

            if start >= seg_start and start < seg_end:
                speaker = seg["speaker"]
                similarity = seg.get("similarity")
                segment_start = seg_start
                segment_end = seg_end
                break
            elif start < seg_start and end > seg_start:
                speaker = seg["speaker"]
                similarity = seg.get("similarity")
                segment_start = seg_start
                segment_end = seg_end
                break

        merged.append({
            "token": token,
            "start": start,
            "end": end,
            "speaker": speaker,
            "similarity": similarity,
            "segment_start": segment_start,
            "segment_end": segment_end
        })

    result = []
    if merged:
        current = {
            "text": merged[0]["token"],
            "start": merged[0]["segment_start"],
            "end": merged[0]["segment_end"],
            "speaker": merged[0]["speaker"],
            "similarity": merged[0]["similarity"]
        }

        for item in merged[1:]:
            if item["speaker"] == current["speaker"]:
                current["text"] += item["token"]
                current["end"] = item["segment_end"]
            else:
                result.append(current)
                current = {
                    "text": item["token"],
                    "start": item["segment_start"],
                    "end": item["segment_end"],
                    "speaker": item["speaker"],
                    "similarity": item["similarity"]
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

            model = model.lower()

            if "fun-asr" in model or "funasr" in model:
                # 使用 Fun-ASR + Cam++ 进行识别和说话人分割
                fun_asr_model = diarization_service.load_fun_asr()
                asr_result = fun_asr_model.generate(
                    input=[tmp_path],
                    language="auto",
                    itn=True,
                    hotwords=asr_service.get_hotwords_text(),
                )
                result_data = asr_result[0]
                print(f"result_data:{result_data}")
                full_text = result_data.get("text", "")

                # 提取说话人embedding
                spk_embedding = result_data.get("spk_embedding", [])
                if spk_embedding and len(spk_embedding) > 0:
                    spk_embedding = spk_embedding[0].get("embedding", [])

                # 从Fun-ASR结果中提取说话人信息
                segments = result_data.get("segments", [])
                if segments:
                    merged_segments = []
                    for seg in segments:
                        text = seg.get("text", "")
                        start = seg.get("start", 0)
                        end = seg.get("end", 0)
                        speaker = seg.get("speaker", "SPEAKER_UNKNOWN")
                        merged_segments.append({
                            "text": text,
                            "start": start,
                            "end": end,
                            "speaker": speaker,
                        })
                    merged_segments = merged_segments
                else:
                    merged_segments = []

                last_speaker = None
                if merged_segments:
                    for seg in reversed(merged_segments):
                        if seg.get("speaker") and seg["speaker"] != "SPEAKER_UNKNOWN":
                            last_speaker = seg["speaker"]
                            break
                    if not last_speaker:
                        last_speaker = merged_segments[-1].get("speaker")

            else:
                # 使用 Qwen-ASR + pyannote 进行识别和说话人分割
                asr_result = asr_service.qwen_asr.transcribe(
                    audio=[tmp_path],
                    language="Chinese",
                    return_time_stamps=True,
                )
                full_text = asr_result[0].text
                timestamps = asr_result[0].time_stamps.items

                logger.info("每个字的timestamp：" + str(timestamps))
                speaker_segments = diarization_service.diarize(tmp_path, num_speakers)
                logger.info("说话人聚类结果：" + str(speaker_segments))

                if settings.wespeaker_enabled and speaker_verify_service._model:
                    speaker_segments = speaker_verify_service.verify_and_merge(
                        tmp_path,
                        speaker_segments,
                        similarity_threshold=0.7
                    )
                    logger.info("wespeaker聚类结果：" + str(speaker_segments))

                merged_segments = merge_asr_and_speaker(timestamps, speaker_segments)

                last_speaker = None
                if merged_segments:
                    for seg in reversed(merged_segments):
                        if seg.get("speaker") and seg["speaker"] != "SPEAKER_UNKNOWN":
                            last_speaker = seg["speaker"]
                            break
                    if not last_speaker:
                        last_speaker = merged_segments[-1].get("speaker")

            return TranscriptionResult(
                text=full_text,
                last_speaker=last_speaker,
                segments=merged_segments
            )
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))