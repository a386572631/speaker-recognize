import io
import os
import base64
import tempfile
import uuid
from typing import List, Optional, Tuple

from pydub import AudioSegment

from .models import get_asr_model
from .config import get_settings
from .utils import (
    parse_speaker_segments,
    merge_to_speaker_segments,
    fix_unknown_speaker,
    fetch_hotwords_from_api,
    compute_segment_similarity,
)


GLOBAL_HOTWORDS: List[str] = []


def init_hotwords():
    global GLOBAL_HOTWORDS
    GLOBAL_HOTWORDS = fetch_hotwords_from_api()
    print(f"已加载 {len(GLOBAL_HOTWORDS)} 条热词")


def _load_hotwords() -> List[str]:
    return [hw.strip('"') for hw in GLOBAL_HOTWORDS]


def _load_hotwords_for_qwen() -> str:
    return " ".join(hw.strip('"') for hw in GLOBAL_HOTWORDS)


def _run_speaker_diarization(
    audio_path: str, pipeline, num_speakers: int = 0
) -> Tuple[List[Tuple[float, float, str]], List[dict]]:
    print(f"当前设置的说话人数:{num_speakers}")
    from pyannote.audio.pipelines.utils.hook import ProgressHook

    with ProgressHook() as hook:
        if num_speakers > 0:
            output = pipeline(audio_path, hook=hook, num_speakers=num_speakers)
        else:
            output = pipeline(audio_path, hook=hook, min_speakers=1, max_speakers=2)

    speaker_str = ""
    for turn, speaker in output.speaker_diarization:
        speaker_str += (
            f"start={turn.start:.3f}s stop={turn.end:.3f}s speaker_{speaker} "
        )

    segments = parse_speaker_segments(speaker_str)

    asr = get_asr_model()
    wespeaker_model = asr.wespeaker_model
    similarity_info = compute_segment_similarity(audio_path, segments, wespeaker_model)

    return segments, similarity_info


def _run_speaker_diarization_funasr(
    audio_path: str,
) -> Tuple[List[Tuple[float, float, str]], List[dict]]:
    asr = get_asr_model()
    funasr_model = asr.funasr_spk_model

    results = funasr_model.generate(
        input=audio_path, batch_size_s=300, spk_diarization=True
    )

    if not results or not results[0].get("sentence_info"):
        return [], []

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
    print(f"segments:{segments}")
    segments = sorted(segments, key=lambda x: x[0])

    wespeaker_model = asr.wespeaker_model
    similarity_info = compute_segment_similarity(audio_path, segments, wespeaker_model)

    return segments, similarity_info


def transcribe_audio(
    audio_path: str, use_diarization: bool = False, num_speakers: int = 0
) -> List[dict]:
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
        funasr_nano_kwargs = asr.funasr_nano_kwargs.copy()
        hotwords = _load_hotwords()
        if hotwords:
            funasr_nano_kwargs["hotwords"] = hotwords
        results = funasr_nano.inference(data_in=[audio_path], **funasr_nano_kwargs)
        text = results[0][0].get("text", "")
        print(f"results:{results}")
        if not use_diarization:
            return [
                {
                    "text": text,
                    "speaker": "SPEAKER_1",
                    "start_time": 0.0,
                    "end_time": 0.0,
                    "similarity": None,
                }
            ]

        if settings.use_funasr_diarization:
            speaker_segments, similarity_info = _run_speaker_diarization_funasr(
                audio_path
            )
        else:
            speaker_segments, similarity_info = _run_speaker_diarization(
                audio_path, pipeline, num_speakers
            )

        if not speaker_segments:
            return [
                {
                    "text": text,
                    "speaker": "SPEAKER_1",
                    "start_time": 0.0,
                    "end_time": 0.0,
                    "similarity": None,
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

        speaker_segments_result = merge_to_speaker_segments(
            items, speaker_segments, similarity_info
        )
        speaker_segments_result = fix_unknown_speaker(speaker_segments_result)
        return speaker_segments_result
    else:
        model = asr.qwen_model
        hotwords = _load_hotwords_for_qwen()
        results = model.transcribe(
            audio=audio_path,
            language="Chinese",
            return_time_stamps=True,
            context=hotwords,
        )

        if not use_diarization:
            return [
                {
                    "text": results[0].text,
                    "speaker": "SPEAKER_1",
                    "start_time": 0.0,
                    "end_time": 0.0,
                    "similarity": None,
                }
            ]

        if settings.use_funasr_diarization:
            speaker_segments, similarity_info = _run_speaker_diarization_funasr(
                audio_path
            )
        else:
            speaker_segments, similarity_info = _run_speaker_diarization(
                audio_path, pipeline, num_speakers
            )

        text = results[0].text
        items = results[0].time_stamps.items

        speaker_segments_result = merge_to_speaker_segments(
            items, speaker_segments, similarity_info
        )
        speaker_segments_result = fix_unknown_speaker(speaker_segments_result)

        return speaker_segments_result


def transcribe_audio_bytes(
    audio_bytes: bytes, use_diarization: bool = True, num_speakers: int = 0
) -> List[dict]:
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

        return transcribe_audio(temp_path, use_diarization, num_speakers)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except:
                pass


def transcribe_audio_base64(
    audio_base64: str, use_diarization: bool = True, num_speakers: int = 0
) -> List[dict]:
    audio_bytes = base64.b64decode(audio_base64)
    return transcribe_audio_bytes(audio_bytes, use_diarization, num_speakers)


def get_last_speaker(segments: List[dict]) -> str:
    if len(segments) > 0:
        last_segment = segments[-1]
        return last_segment.get("speaker", "SPEAKER_1")
    return "SPEAKER_1"
