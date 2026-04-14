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
    align_items: List[Any], speaker_segments: List[Tuple[float, float, str]]
) -> List[dict]:
    print(f"speaker_segments:{speaker_segments}")
    print(f"align_items count: {len(align_items)}")
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

    seg_idx = 0
    for item in align_items:
        char_mid = (item.start_time + item.end_time) / 2
        while seg_idx < len(sorted_segments):
            start, stop, speaker = sorted_segments[seg_idx]
            if char_mid >= start and char_mid <= stop + 0.1:
                break
            seg_idx += 1

        if seg_idx < len(sorted_segments):
            target_speaker = speaker
        else:
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
