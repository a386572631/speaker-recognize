import os
import json
import base64
import tempfile
import uuid
from typing import List, Optional

import numpy as np
from pydub import AudioSegment

from .models import get_asr_model
from .config import get_settings
from .utils import (
    parse_speaker_segments,
    merge_to_speaker_segments,
    fix_unknown_speaker,
)


def transcribe_audio(audio_path: str) -> List[dict]:
    asr = get_asr_model()
    pipeline = asr.pipeline
    settings = get_settings()

    if settings.model_name == "Fun-ASR-Nano-2512":
        funasr_model = asr.funasr_model
        results = funasr_model.generate(input=[audio_path], batch_size_s=300)
        text = results[0].get("text", "")

        from pyannote.audio.pipelines.utils.hook import ProgressHook

        with ProgressHook() as hook:
            output = pipeline(audio_path, hook=hook)

        speaker_str = ""
        for turn, speaker in output.speaker_diarization:
            speaker_str += (
                f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}"
            )

        speaker_segments = parse_speaker_segments(speaker_str)

        return [
            {
                "text": text,
                "speaker": speaker_segments[0].get("speaker", "SPEAKER_1")
                if speaker_segments
                else "SPEAKER_1",
                "start_time": 0.0,
                "end_time": 0.0,
            }
        ]
    else:
        model = asr.qwen_model
        results = model.transcribe(
            audio=audio_path, language="Chinese", return_time_stamps=True
        )

        from pyannote.audio.pipelines.utils.hook import ProgressHook

        with ProgressHook() as hook:
            output = pipeline(audio_path, hook=hook)

        speaker_str = ""
        for turn, speaker in output.speaker_diarization:
            speaker_str += (
                f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}"
            )

        speaker_segments = parse_speaker_segments(speaker_str)
        items = results[0].time_stamps.items
        speaker_segments_result = merge_to_speaker_segments(items, speaker_segments)
        speaker_segments_result = fix_unknown_speaker(speaker_segments_result)

        return speaker_segments_result


def transcribe_audio_bytes(audio_bytes: bytes) -> List[dict]:
    unique_filename = f"{uuid.uuid4()}.wav"
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, unique_filename)

    try:
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)

        return transcribe_audio(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except:
                pass


def transcribe_audio_base64(audio_base64: str) -> List[dict]:
    audio_bytes = base64.b64decode(audio_base64)
    return transcribe_audio_bytes(audio_bytes)


def get_last_speaker(segments: List[dict]) -> str:
    if len(segments) > 0:
        last_segment = segments[-1]
        return last_segment.get("speaker", "SPEAKER_1")
    return "SPEAKER_1"
