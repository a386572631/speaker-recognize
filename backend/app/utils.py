import re
import os
import tempfile
import uuid
import requests
from typing import List, Tuple, Any
from pydub import AudioSegment

from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook


def parse_speaker_segments(speaker_str: str) -> List[Tuple[float, float, str]]:
    segments = []
    pattern = r"start=([\d.]+)s stop=([\d.]+)s speaker_([\w\d]+)"
    matches = re.findall(pattern, speaker_str)
    for match in matches:
        start = float(match[0])
        stop = float(match[1])
        speaker = match[2]
        segments.append((start, stop, speaker))
    segments.sort(key=lambda x: x[0])

    if not segments:
        return segments

    split_segments = []
    current = segments[0]

    for next_seg in segments[1:]:
        if next_seg[0] < current[1]:
            if next_seg[2] != current[2]:
                if current[0] < next_seg[0]:
                    split_segments.append((current[0], next_seg[0], current[2]))
                split_segments.append(
                    (next_seg[0], min(current[1], next_seg[1]), next_seg[2])
                )
                if current[1] > next_seg[1]:
                    split_segments.append((next_seg[1], current[1], current[2]))
                current = next_seg
            else:
                current = (current[0], max(current[1], next_seg[1]), current[2])
        else:
            split_segments.append(current)
            current = next_seg

    split_segments.append(current)
    return split_segments


def merge_to_speaker_segments(
    align_items: List[Any],
    speaker_segments: List[Tuple[float, float, str]],
    similarity_info: List[dict] = None,
) -> List[dict]:
    if not speaker_segments:
        return []

    sorted_segments = sorted(speaker_segments, key=lambda x: x[0])

    result_segments = []
    current_speaker = 1

    for idx, (start, stop, speaker) in enumerate(sorted_segments):
        segment_texts = []

        if align_items:
            for item in align_items:
                char_start = item.start_time
                char_end = item.end_time

                if char_start >= start and char_end <= stop:
                    segment_texts.append(item.text)

        similarity = None
        if similarity_info and idx < len(similarity_info):
            similarity = similarity_info[idx].get("similarity")

        if result_segments:
            prev = result_segments[-1]
            should_merge = similarity is not None and similarity >= 0.7

            if should_merge:
                prev["end_time"] = round(stop, 2)
                if segment_texts:
                    prev["text"] = prev.get("text", "") + "".join(segment_texts)
                continue

            current_speaker += 1

        text = "".join(segment_texts) if segment_texts else ""
        result_segments.append(
            {
                "text": text,
                "speaker": f"SPEAKER_{str(current_speaker).zfill(2)}",
                "start_time": round(start, 2),
                "end_time": round(stop, 2),
                "similarity": similarity,
            }
        )

    return result_segments


def fix_unknown_speaker(segments: List[dict]) -> List[dict]:
    for item in segments:
        if "UNKNOWN" in str(item.get("speaker", "")):
            item["speaker"] = "SPEAKER_1"
    return segments


def fetch_hotwords_from_api() -> List[str]:
    from .config import get_settings

    settings = get_settings()
    if not settings.wfw_base_url or not settings.get_xm_hotwords:
        return []

    url = settings.wfw_base_url + settings.get_xm_hotwords
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get("hasError", 0) != 0:
            print(f"获取热词失败: {result.get('errorMessage', '未知错误')}")
            return []

        data = result.get("data", [])
        if not data:
            return []

        return [str(item) for item in data]
    except Exception as e:
        print(f"获取热词失败: {e}")
        return []


def compute_segment_similarity(
    audio_path: str,
    speaker_segments: List[Tuple[float, float, str]],
    wespeaker_model,
    merge_threshold: float = 0.7,
) -> List[dict]:
    if not speaker_segments or len(speaker_segments) < 2:
        return []

    segments_with_path = []
    temp_dir = tempfile.mkdtemp()

    try:
        for i, (start, end, speaker) in enumerate(speaker_segments):
            audio = AudioSegment.from_file(audio_path)
            segment_audio = audio[int(start * 1000) : int(end * 1000)]
            segment_path = os.path.join(temp_dir, f"segment_{i}_{uuid.uuid4()}.wav")
            segment_audio.export(segment_path, format="wav")

            segments_with_path.append(
                {
                    "start": start,
                    "end": end,
                    "speaker": speaker,
                    "path": segment_path,
                    "similarity": None,
                }
            )

        for i in range(1, len(segments_with_path)):
            prev_seg = segments_with_path[i - 1]
            curr_seg = segments_with_path[i]

            try:
                similarity = wespeaker_model.compute_similarity(
                    prev_seg["path"], curr_seg["path"]
                )
                curr_seg["similarity"] = float(similarity)
            except Exception as e:
                print(f"计算相似度失败: {e}")

    finally:
        for seg in segments_with_path:
            if os.path.exists(seg.get("path", "")):
                try:
                    os.remove(seg["path"])
                except:
                    pass
        try:
            os.rmdir(temp_dir)
        except:
            pass

    results = []
    current_speaker_id = "SPEAKER_01"
    expected_speaker = 1

    for i, seg in enumerate(segments_with_path):
        similarity = seg.get("similarity")

        if results:
            prev = results[-1]
            should_merge = similarity is not None and similarity >= merge_threshold

            if should_merge:
                prev["end"] = seg["end"]
                continue

            expected_speaker += 1

        current_speaker_id = f"SPEAKER_{str(expected_speaker).zfill(2)}"
        results.append(
            {
                "start": seg["start"],
                "end": seg["end"],
                "speaker": current_speaker_id,
                "similarity": similarity,
            }
        )

    return results
