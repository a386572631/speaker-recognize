import re
from typing import List, Tuple, Any

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
    return segments


def merge_to_speaker_segments(
    align_items: List[Any], speaker_segments: List[Tuple[float, float, str]]
) -> List[dict]:
    if not align_items or not speaker_segments:
        return []

    speaker_labels = {}
    speaker_counter = 1
    sorted_segments = sorted(speaker_segments, key=lambda x: x[0])
    for _, _, speaker in sorted_segments:
        if speaker not in speaker_labels:
            speaker_labels[speaker] = f"SPEAKER_{speaker_counter}"
            speaker_counter += 1

    result_segments = []
    current_speaker = None
    current_text = []
    current_start_time = None
    current_end_time = None

    for item in align_items:
        char_mid = (item.start_time + item.end_time) / 2
        target_speaker = None
        for start, stop, speaker in speaker_segments:
            if start - 0.05 <= char_mid <= stop + 0.05:
                target_speaker = speaker
                break

        if target_speaker is None:
            target_speaker = current_speaker

        if target_speaker != current_speaker:
            if current_text:
                result_segments.append(
                    {
                        "text": "".join(current_text),
                        "speaker": speaker_labels.get(
                            current_speaker, "SPEAKER_UNKNOWN"
                        ),
                        "start_time": current_start_time,
                        "end_time": current_end_time,
                    }
                )
            current_speaker = target_speaker
            current_text = [item.text]
            current_start_time = item.start_time
            current_end_time = item.end_time
        else:
            current_text.append(item.text)
            current_end_time = item.end_time

    if current_text:
        result_segments.append(
            {
                "text": "".join(current_text),
                "speaker": speaker_labels.get(current_speaker, "SPEAKER_UNKNOWN"),
                "start_time": current_start_time,
                "end_time": current_end_time,
            }
        )

    merged_result = []
    for segment in result_segments:
        if merged_result and merged_result[-1]["speaker"] == segment["speaker"]:
            merged_result[-1]["text"] += segment["text"]
            merged_result[-1]["end_time"] = segment["end_time"]
        else:
            merged_result.append(segment)

    return merged_result


def fix_unknown_speaker(segments: List[dict]) -> List[dict]:
    for item in segments:
        if "UNKNOWN" in str(item.get("speaker", "")):
            item["speaker"] = "SPEAKER_1"
    return segments
