import os
import io
import json
import base64
import tempfile
import uuid
from typing import List, Optional, Tuple

import numpy as np
from pydub import AudioSegment

from .models import get_asr_model
from .config import get_settings
from .utils import (
    parse_speaker_segments,
    merge_to_speaker_segments,
    fix_unknown_speaker,
)


def _run_speaker_diarization(
    audio_path: str, pipeline
) -> List[Tuple[float, float, str]]:
    from pyannote.audio.pipelines.utils.hook import ProgressHook

    with ProgressHook() as hook:
        output = pipeline(audio_path, hook=hook, min_speakers=1, max_speakers=3)

    speaker_str = ""
    for turn, speaker in output.speaker_diarization:
        speaker_str += (
            f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker} "
        )

    return parse_speaker_segments(speaker_str)


def _run_speaker_diarization_funasr(audio_path: str) -> List[Tuple[float, float, str]]:
    asr = get_asr_model()
    funasr_model = asr.funasr_spk_model

    results = funasr_model.generate(
        input=audio_path, batch_size_s=300, spk_diarization=True
    )

    if not results or not results[0].get("sentence_info"):
        return []

    segments = []
    speaker_counter = 1
    speaker_labels = {}

    for sentence in results[0]["sentence_info"]:
        spk = sentence.get("spk", 0)
        if spk not in speaker_labels:
            speaker_labels[spk] = f"SPEAKER_{speaker_counter}"
            speaker_counter += 1

        segments.append(
            (
                sentence.get("start", 0) / 1000.0,
                sentence.get("end", 0) / 1000.0,
                speaker_labels[spk],
            )
        )

    return sorted(segments, key=lambda x: x[0])


def transcribe_audio(audio_path: str) -> List[dict]:
    if audio_path.endswith(".webm"):
        audio = AudioSegment.from_file(audio_path, format="webm")
        audio = audio.set_frame_rate(16000).set_channels(2)
        new_path = audio_path.replace(".webm", ".wav")
        audio.export(new_path, format="wav")
        os.remove(audio_path)
        audio_path = new_path

    asr = get_asr_model()
    pipeline = asr.pipeline
    settings = get_settings()

    if settings.model_name == "Fun-ASR-Nano-2512":
        funasr_nano = asr.funasr_nano_model
        funasr_nano_kwargs = asr.funasr_nano_kwargs
        results = funasr_nano.inference(data_in=[audio_path], **funasr_nano_kwargs)
        text = results[0][0].get("text", "")

        if settings.use_funasr_diarization:
            speaker_segments = _run_speaker_diarization_funasr(audio_path)
        else:
            speaker_segments = _run_speaker_diarization(audio_path, pipeline)

        if not speaker_segments:
            return [
                {
                    "text": text,
                    "speaker": "SPEAKER_1",
                    "start_time": 0.0,
                    "end_time": 0.0,
                }
            ]

        from typing import NamedTuple

        class ForcedAlignItem(NamedTuple):
            text: str
            start_time: float
            end_time: float

        items = []
        for i in results[0][0].get("timestamps", []):
            items.append(
                ForcedAlignItem(
                    text=i["token"], start_time=i["start_time"], end_time=i["end_time"]
                )
            )

        speaker_segments_result = merge_to_speaker_segments(items, speaker_segments)
        speaker_segments_result = fix_unknown_speaker(speaker_segments_result)
        return speaker_segments_result
    else:
        model = asr.qwen_model
        results = model.transcribe(
            audio=audio_path, language="Chinese", return_time_stamps=True
        )

        if settings.use_funasr_diarization:
            speaker_segments = _run_speaker_diarization_funasr(audio_path)
        else:
            speaker_segments = _run_speaker_diarization(audio_path, pipeline)

        items = results[0].time_stamps.items

        speaker_segments_result = merge_to_speaker_segments(items, speaker_segments)
        speaker_segments_result = fix_unknown_speaker(speaker_segments_result)

        return speaker_segments_result


def transcribe_audio_bytes(audio_bytes: bytes) -> List[dict]:
    audio_bytesio = io.BytesIO(audio_bytes)
    audio_bytesio.seek(0)
    header_bytes = audio_bytesio.read(16)
    audio_bytesio.seek(0)

    if header_bytes[:4] == b"\x1aE\xdf\xa3":
        unique_filename = f"{uuid.uuid4()}.webm"
    else:
        unique_filename = f"{uuid.uuid4()}.wav"

    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, unique_filename)

    try:
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)

        if temp_path.endswith(".webm"):
            audio = AudioSegment.from_file(temp_path, format="webm")
            audio = audio.set_frame_rate(16000).set_channels(2)
            new_path = os.path.join(temp_dir, f"{uuid.uuid4()}.wav")
            audio.export(new_path, format="wav")
            os.remove(temp_path)
            temp_path = new_path

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
